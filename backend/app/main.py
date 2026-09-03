import hashlib
import json
import io
import os
import time
import uuid
import zipfile
from collections import defaultdict, deque

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from .config import settings
from .db import Base, engine, get_db
from .models import User, Case, Document, DocumentVersion, AuditEvent
from .schemas import (
    Token, UserOut, LoginIn, CaseCreateIn, CaseOut, DocumentOut,
    VersionOut, AuditOut, SearchResultOut,
)
from .security import current_user, create_token, verify_password
from .storage import ensure_bucket, put_bytes, get_bytes, delete_bytes
from .authorization import Permission, require_permission, has_permission
from .trust_ledger import ensure_ledger, anchor_audit_event, list_blocks, verify_ledger, document_anchors
from .custody import build_custody_record
from .blockchain import status as blockchain_status, anchor as blockchain_anchor, read as blockchain_read, custody_digest
from .incidents import ensure_incidents, open_integrity_incident, list_incidents, resolve_incident
from .governance import ensure_governance, create_share, list_shares, revoke_share, sign_record, list_signatures, verify_signature, set_retention, set_hold, governance
from datetime import datetime, timezone, timedelta


app = FastAPI(title="KAIRO API", version="1.0.0")

# Prototype hardening. Production deployment should use a reverse proxy/WAF
# and a distributed rate limiter for multiple API instances.
_LOGIN_WINDOW = 60
_LOGIN_MAX_ATTEMPTS = 8
_login_attempts = defaultdict(deque)

@app.middleware("http")
async def security_headers(request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response

def _check_login_rate_limit(client_host: str):
    now = time.time()
    q = _login_attempts[client_host]
    while q and now - q[0] > _LOGIN_WINDOW:
        q.popleft()
    if len(q) >= _LOGIN_MAX_ATTEMPTS:
        raise HTTPException(429, "Too many login attempts. Try again later.")
    q.append(now)



app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    ensure_bucket()
    with Session(engine) as db:
        ensure_ledger(db)
        ensure_incidents(db)
        ensure_governance(db)


def audit(
    db: Session,
    actor: User | None,
    action: str,
    target_type: str,
    target_id: str | int,
    result: str,
    details: str = "",
):
    event = AuditEvent(
        actor_id=actor.id if actor else None,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        result=result,
        details=details,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    anchor_audit_event(db, event)


def deny(
    db: Session,
    user: User,
    action: str,
    target_type: str,
    target_id: str | int,
    reason: str,
):
    audit(
        db,
        user,
        action,
        target_type,
        target_id,
        "DENIED",
        json.dumps({"reason": reason, "role": user.role}),
    )
    raise HTTPException(
        status_code=403,
        detail={
            "code": "FORBIDDEN",
            "message": "Your role is not authorized for this action.",
            "role": user.role,
        },
    )


@app.get("/api/health")
def health():
    """Readiness-style health without exposing infrastructure secrets."""
    checks = {"api": "ok", "database": "unknown", "evidence_store": "unknown", "trust_ledger": "unknown"}
    overall = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"
        overall = "degraded"

    try:
        ensure_bucket()
        checks["evidence_store"] = "ok"
    except Exception:
        checks["evidence_store"] = "unavailable"
        overall = "degraded"

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM trust_blocks LIMIT 1"))
        checks["trust_ledger"] = "ok"
    except Exception:
        checks["trust_ledger"] = "unavailable"
        overall = "degraded"

    return {"status": overall, "service": "kairo-api", "checks": checks}


@app.post("/api/auth/login", response_model=Token)
def login(body: LoginIn, db: Session = Depends(get_db)):
    _check_login_rate_limit("anonymous:" + (body.email or "").lower().strip())
    user = db.scalar(select(User).where(User.email == body.email.lower().strip()))

    if not user or not verify_password(body.password, user.password_hash):
        audit(
            db,
            user,
            "LOGIN",
            "USER",
            body.email,
            "DENIED",
            "Invalid credentials",
        )
        raise HTTPException(401, "Invalid credentials")

    if not user.is_active:
        audit(
            db,
            user,
            "LOGIN",
            "USER",
            user.id,
            "DENIED",
            "Inactive account",
        )
        raise HTTPException(403, "Account is inactive")

    audit(
        db,
        user,
        "LOGIN",
        "USER",
        user.id,
        "SUCCESS",
        "Interactive login",
    )
    return Token(access_token=create_token(user))


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@app.get("/api/auth/permissions")
def my_permissions(user: User = Depends(current_user)):
    permissions = sorted(p.value for p in
                        __import__("app.authorization", fromlist=["ROLE_PERMISSIONS"])
                        .ROLE_PERMISSIONS.get(user.role, frozenset()))
    return {
        "user_id": user.id,
        "role": user.role,
        "permissions": permissions,
    }


@app.get("/api/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return {
        "cases": db.scalar(select(func.count()).select_from(Case)) or 0,
        "documents": db.scalar(select(func.count()).select_from(Document)) or 0,
        "versions": db.scalar(select(func.count()).select_from(DocumentVersion)) or 0,
        "audit_events": db.scalar(select(func.count()).select_from(AuditEvent)) or 0,
        "trust_blocks": db.execute(__import__("sqlalchemy").text("SELECT COUNT(*) FROM trust_blocks")).scalar() or 0,
        "role": user.role,
    }


@app.get(
    "/api/cases",
    response_model=list[CaseOut],
)
def cases(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.CASE_READ)),
):
    return list(db.scalars(select(Case).order_by(Case.created_at.desc())))


@app.post("/api/cases", response_model=CaseOut, status_code=201)
def create_case(
    body: CaseCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.CASE_CREATE)),
):
    case_number = body.case_number.strip()
    if not case_number or not body.title.strip() or not body.station.strip():
        raise HTTPException(422, "Case number, title and station are required.")
    if db.scalar(select(Case).where(Case.case_number == case_number)):
        raise HTTPException(409, "Case number already exists.")
    if body.priority not in {"HIGH", "MEDIUM", "LOW"}:
        raise HTTPException(422, "Priority must be HIGH, MEDIUM or LOW.")
    case = Case(case_number=case_number, title=body.title.strip(), description=body.description.strip(), priority=body.priority, station=body.station.strip(), status="UNDER_INVESTIGATION", is_demo=False)
    db.add(case)
    db.commit()
    db.refresh(case)
    audit(db, user, "CASE_CREATED", "CASE", case.id, "SUCCESS", json.dumps({"case_number": case.case_number}))
    return case


@app.get(
    "/api/cases/{case_id}",
    response_model=CaseOut,
)
def case_detail(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.CASE_READ)),
):
    item = db.get(Case, case_id)
    if not item:
        raise HTTPException(404, "Case not found")
    return item


@app.get(
    "/api/cases/{case_id}/documents",
    response_model=list[DocumentOut],
)
def case_documents(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.DOCUMENT_READ)),
):
    if not db.get(Case, case_id):
        raise HTTPException(404, "Case not found")

    return list(
        db.scalars(
            select(Document)
            .where(Document.case_id == case_id)
            .order_by(Document.created_at)
        )
    )


@app.get("/api/search", response_model=list[SearchResultOut])
def search(
    q: str = "", case_id: int | None = None, document_type: str | None = None,
    classification: str | None = None, limit: int = 50, offset: int = 0,
    db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.DOCUMENT_READ)),
):
    """Search case/document metadata and the latest registered evidence filename."""
    q = q.strip(); limit = max(1, min(limit, 100)); offset = max(0, offset)
    latest = select(
        DocumentVersion.document_id.label("document_id"),
        DocumentVersion.original_filename.label("filename"),
        DocumentVersion.sha256.label("sha256"),
        func.row_number().over(partition_by=DocumentVersion.document_id, order_by=DocumentVersion.version.desc()).label("rn"),
    ).subquery()
    stmt = (select(Document, Case, latest.c.filename, latest.c.sha256)
        .join(Case, Document.case_id == Case.id)
        .outerjoin(latest, (latest.c.document_id == Document.id) & (latest.c.rn == 1))
        .order_by(Document.created_at.desc()).offset(offset).limit(limit))
    filters=[]
    if case_id is not None: filters.append(Document.case_id == case_id)
    if document_type: filters.append(Document.document_type == document_type.upper())
    if classification: filters.append(Document.classification == classification.upper())
    if q:
        pattern=f"%{q}%"
        filters.append(or_(Document.document_number.ilike(pattern), Document.title.ilike(pattern),
            Document.document_type.ilike(pattern), Document.classification.ilike(pattern), Case.case_number.ilike(pattern),
            Case.title.ilike(pattern), Case.description.ilike(pattern), Case.station.ilike(pattern), latest.c.filename.ilike(pattern)))
    if filters: stmt=stmt.where(*filters)
    rows=db.execute(stmt).all()
    return [SearchResultOut(document_id=d.id, document_number=d.document_number, title=d.title,
        document_type=d.document_type, classification=d.classification, current_version=d.current_version,
        case_id=c.id, case_number=c.case_number, case_title=c.title, filename=f, sha256=h, created_at=d.created_at)
        for d,c,f,h in rows]


@app.get(
    "/api/documents/{document_id}",
    response_model=DocumentOut,
)
def document_detail(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.DOCUMENT_READ)),
):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@app.get(
    "/api/documents/{document_id}/versions",
    response_model=list[VersionOut],
)
def document_versions(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.DOCUMENT_READ)),
):
    if not db.get(Document, document_id):
        raise HTTPException(404, "Document not found")

    return list(
        db.scalars(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version.desc())
        )
    )


@app.post(
    "/api/cases/{case_id}/documents",
    response_model=DocumentOut,
)
async def upload_document(
    case_id: int,
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: str = Form(...),
    classification: str = Form("RESTRICTED"),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.DOCUMENT_UPLOAD)),
):
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    if classification.upper() not in {"RESTRICTED", "CONFIDENTIAL", "HIGHLY_RESTRICTED"}:
        deny(
            db, user, "DOCUMENT_UPLOAD", "CASE", case_id,
            "Unsupported classification",
        )

    if user.role == "FORENSIC_OFFICER" and document_type.upper() not in {
        "FORENSIC_REPORT", "FORENSIC", "EVIDENCE"
    }:
        deny(
            db, user, "DOCUMENT_UPLOAD", "CASE", case_id,
            "Forensic officer may upload only forensic/evidence document types",
        )

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file is not allowed")
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "File exceeds the 25 MB prototype upload limit.")

    sha = hashlib.sha256(data).hexdigest()
    count = db.scalar(select(func.count()).select_from(Document)) or 0

    doc = Document(
        document_number=f"KAIRO-DOC-{count + 1:05d}",
        case_id=case_id,
        title=title,
        document_type=document_type,
        classification=classification.upper(),
        current_version=1,
    )

    db.add(doc)
    db.flush()

    key = (
        f"cases/{case.case_number}/documents/{doc.id}/"
        f"v1/{file.filename}"
    )

    try:
        put_bytes(key, data, file.content_type or "application/octet-stream")
        db.add(DocumentVersion(
            document_id=doc.id,
            version=1,
            object_key=key,
            original_filename=file.filename or "evidence",
            content_type=file.content_type or "application/octet-stream",
            size_bytes=len(data),
            sha256=sha,
            uploaded_by=user.id,
        ))
        db.commit()
    except Exception as exc:
        db.rollback()
        try:
            delete_bytes(key)
        except Exception:
            pass
        raise HTTPException(503, "Evidence storage could not be committed. No document was registered.") from exc

    audit(
        db,
        user,
        "DOCUMENT_UPLOAD",
        "DOCUMENT",
        doc.id,
        "SUCCESS",
        json.dumps({
            "sha256": sha,
            "version": 1,
            "case_id": case_id,
            "classification": classification.upper(),
        }),
    )

    db.refresh(doc)
    return doc



@app.post("/api/documents/{document_id}/versions", response_model=VersionOut)
async def create_document_version(
    document_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.DOCUMENT_VERSION_CREATE)),
):
    """
    Append a new immutable document version.

    Existing versions are never overwritten. The new object is stored under
    a new versioned object key and gets its own SHA-256 fingerprint.
    """
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file is not allowed")
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "File exceeds the 25 MB prototype upload limit.")

    latest = db.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version.desc())
    )
    sha = hashlib.sha256(data).hexdigest()
    if latest and latest.sha256 == sha:
        raise HTTPException(409, "No new version created: the submitted file is identical to the current registered evidence version.")
    next_version = (latest.version if latest else 0) + 1

    case = db.get(Case, doc.case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    key = (
        f"cases/{case.case_number}/documents/{doc.id}/"
        f"v{next_version}/{file.filename}"
    )

    try:
        put_bytes(key, data, file.content_type or "application/octet-stream")
        version = DocumentVersion(
            document_id=doc.id,
            version=next_version,
            object_key=key,
            original_filename=file.filename or "evidence",
            content_type=file.content_type or "application/octet-stream",
            size_bytes=len(data),
            sha256=sha,
            uploaded_by=user.id,
        )
        db.add(version)
        doc.current_version = next_version
        db.commit()
        db.refresh(version)
    except Exception as exc:
        db.rollback()
        try:
            delete_bytes(key)
        except Exception:
            pass
        raise HTTPException(503, "Evidence version could not be committed. The registered version was not changed.") from exc

    audit(
        db,
        user,
        "DOCUMENT_VERSION_CREATE",
        "DOCUMENT",
        doc.id,
        "SUCCESS",
        json.dumps({
            "version": next_version,
            "sha256": sha,
            "previous_version": latest.version if latest else None,
        }),
    )
    return version

@app.post("/api/documents/{document_id}/verify")
def verify_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.DOCUMENT_VERIFY)),
):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    version = db.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version.desc())
    )

    if not version:
        raise HTTPException(404, "Document has no version")

    data = get_bytes(version.object_key)
    observed = hashlib.sha256(data).hexdigest()
    verified = observed == version.sha256
    result = "VERIFIED" if verified else "FAILED"

    audit(
        db,
        user,
        "INTEGRITY_VERIFY",
        "DOCUMENT",
        doc.id,
        result,
        json.dumps({
            "version": version.version,
            "expected": version.sha256,
            "observed": observed,
        }),
    )

    custody = build_custody_record(db, document_id, verify_bytes=False)

    incident_id = None
    if not verified:
        authorized_event_id = None
        if custody and custody.get("authorized_change"):
            authorized_event_id = custody["authorized_change"].get("event_id")
        incident_id, _ = open_integrity_incident(
            db, doc.id, version.version, user.id, version.sha256, observed, authorized_event_id
        )
        audit(
            db, user, "SECURITY_INCIDENT_OPEN", "DOCUMENT", doc.id, "SUCCESS",
            json.dumps({"incident_id": incident_id, "incident_type": "UNAUTHORIZED_MODIFICATION", "version": version.version})
        )

    return {
        "document_id": doc.id,
        "version": version.version,
        "expected_sha256": version.sha256,
        "observed_sha256": observed,
        "verified": verified,
        "result": result,
        "custody": custody,
        "incident_id": incident_id,
    }


@app.get("/api/incidents")
def incidents(
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return list_incidents(db, status=status)


@app.post("/api/incidents/{incident_id}/resolve")
def incident_resolve(
    incident_id: int,
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.TRUST_READ)),
):
    resolution = str(body.get("resolution", "")).strip()
    if len(resolution) < 8:
        raise HTTPException(400, "Resolution must contain at least 8 characters")
    if not resolve_incident(db, incident_id, user.id, resolution):
        raise HTTPException(404, "Open incident not found")
    audit(db, user, "SECURITY_INCIDENT_RESOLVE", "INCIDENT", incident_id, "SUCCESS", resolution)
    return {"ok": True, "incident_id": incident_id, "status": "RESOLVED"}


@app.get("/api/blockchain/status")
def blockchain_connection_status(
    user: User = Depends(current_user),
):
    return blockchain_status()


@app.post("/api/documents/{document_id}/blockchain-anchor")
def blockchain_anchor_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.TRUST_READ)),
):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    custody = build_custody_record(db, document_id, verify_bytes=True)
    if not custody:
        raise HTTPException(404, "Document has no custody record")
    current = custody.get("current_version") or {}
    if not current.get("verified"):
        raise HTTPException(409, "Refusing blockchain anchor: current evidence failed integrity verification")
    version = current.get("version")
    evidence_hash = current.get("sha256")
    anchor_id = f"KAIRO-{doc.document_number}-V{version}"
    payload = {
        "anchorId": anchor_id,
        "documentId": doc.document_number,
        "version": version,
        "evidenceHash": evidence_hash,
        "custodyHash": custody_digest(custody),
        "actor": user.email,
        "action": "DOCUMENT_TRUST_ANCHOR",
    }
    result = blockchain_anchor(payload)
    audit(db, user, "BLOCKCHAIN_ANCHOR", "DOCUMENT", doc.id, "SUCCESS" if result.get("ok") else "FAILED", json.dumps(result))
    if not result.get("ok"):
        raise HTTPException(503, detail={"code":"BLOCKCHAIN_UNAVAILABLE", "message":result.get("message", "Blockchain gateway unavailable")})
    return {"document": doc.document_number, "anchor_id": anchor_id, "fabric": result.get("record"), "evidence_sha256": evidence_hash, "custody_sha256": payload["custodyHash"]}


@app.get("/api/documents/{document_id}/blockchain-anchor")
def blockchain_anchor_document_read(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.TRUST_READ)),
):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    version = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.version.desc()))
    if not version:
        raise HTTPException(404, "Document has no version")
    anchor_id = f"KAIRO-{doc.document_number}-V{version.version}"
    return blockchain_read(anchor_id)


@app.get("/api/trust/ledger")
def trust_ledger(
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.TRUST_READ)),
):
    limit = max(1, min(limit, 200))
    status = verify_ledger(db)
    return {"status": status, "blocks": list_blocks(db, limit)}


@app.get("/api/trust/verify")
def trust_verify(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.TRUST_READ)),
):
    result = verify_ledger(db)
    audit(
        db, user, "TRUST_LEDGER_VERIFY", "TRUST_LEDGER", "GLOBAL",
        "VERIFIED" if result["verified"] else "FAILED",
        json.dumps({"blocks": result["blocks"], "failures": result["failures"]}),
    )
    return result


@app.get("/api/documents/{document_id}/custody")
def document_custody(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.DOCUMENT_VERIFY)),
):
    record = build_custody_record(db, document_id, verify_bytes=True)
    if record is None:
        raise HTTPException(404, "Document not found")
    return record


@app.get("/api/documents/{document_id}/trust")
def document_trust(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.TRUST_READ)),
):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return {"document_id": document_id, "anchors": document_anchors(db, document_id)}



@app.get("/api/users/collaborators")
def collaborators(db: Session = Depends(get_db), user: User = Depends(require_permission(Permission.DOCUMENT_READ))):
    rows = db.execute(__import__("sqlalchemy").text("SELECT id,email,full_name,role FROM users WHERE is_active=TRUE AND id<>:u ORDER BY full_name"), {"u": user.id}).mappings().all()
    return [dict(r) for r in rows]

@app.post("/api/documents/{document_id}/shares")
def share_document(document_id:int, body:dict, db:Session=Depends(get_db), user:User=Depends(require_permission(Permission.DOCUMENT_READ))):
    doc=db.get(Document,document_id)
    if not doc: raise HTTPException(404,"Document not found")
    target=db.scalar(select(User).where(User.email==str(body.get("email","")).lower().strip()))
    if not target or not target.is_active: raise HTTPException(404,"Authorized collaborator not found")
    if target.id==user.id: raise HTTPException(400,"Choose another authorized collaborator")
    permission=str(body.get("permission","VIEW")).upper()
    if permission not in {"VIEW","DOWNLOAD"}: raise HTTPException(400,"Unsupported share permission")
    try: expires=datetime.fromisoformat(str(body.get("expires_at")).replace("Z","+00:00"))
    except Exception: raise HTTPException(400,"expires_at must be an ISO timestamp")
    if expires <= datetime.now(timezone.utc): raise HTTPException(400,"Share must expire in the future")
    result=create_share(db,document_id,user.id,target.id,permission,expires)
    audit(db,user,"DOCUMENT_SHARE","DOCUMENT",document_id,"SUCCESS",json.dumps({"shared_with":target.email,"permission":permission,"expires_at":expires.isoformat()}))
    return {"id":result["id"],"token":result["token"],"expires_at":expires,"shared_with":target.email,"permission":permission}

@app.get("/api/shares/incoming")
def incoming_shares(db:Session=Depends(get_db), user:User=Depends(current_user)):
    return list_shares(db,user.id,incoming=True)

@app.get("/api/shares/outgoing")
def outgoing_shares(db:Session=Depends(get_db), user:User=Depends(require_permission(Permission.DOCUMENT_READ))):
    return list_shares(db,user.id,incoming=False)

@app.get("/api/shares/{share_id}/download")
def download_shared_document(share_id:int, db:Session=Depends(get_db), user:User=Depends(current_user)):
    row=db.execute(__import__("sqlalchemy").text("""SELECT s.*,d.document_number,d.title,v.version,v.object_key,v.original_filename,v.content_type,v.sha256
      FROM document_shares s JOIN documents d ON d.id=s.document_id
      JOIN document_versions v ON v.document_id=d.id AND v.version=d.current_version
      WHERE s.id=:i AND s.shared_with=:u"""),{"i":share_id,"u":user.id}).mappings().first()
    if not row: raise HTTPException(404,"Share not found")
    now=datetime.now(timezone.utc)
    if row["revoked_at"]: raise HTTPException(403,"Share has been revoked")
    if row["expires_at"] <= now: raise HTTPException(403,"Share has expired")
    if row["permission"] not in {"VIEW","DOWNLOAD"}: raise HTTPException(403,"Share does not permit retrieval")
    data=get_bytes(row["object_key"]); observed=hashlib.sha256(data).hexdigest()
    if observed != row["sha256"]: raise HTTPException(409,"Refusing shared retrieval: evidence failed integrity verification")
    audit(db,user,"SHARED_DOCUMENT_DOWNLOAD","DOCUMENT",row["document_id"],"SUCCESS",json.dumps({"share_id":share_id,"version":row["version"]}))
    return Response(content=data,media_type=row["content_type"],headers={"Content-Disposition":f'attachment; filename="{row["original_filename"]}"'})

@app.post("/api/shares/{share_id}/revoke")
def revoke_document_share(share_id:int, db:Session=Depends(get_db), user:User=Depends(require_permission(Permission.DOCUMENT_READ))):
    row=revoke_share(db,share_id,user.id)
    if not row: raise HTTPException(404,"Share not found or not owned by you")
    audit(db,user,"DOCUMENT_SHARE_REVOKE","SHARE",share_id,"SUCCESS","")
    return {"ok":True,"id":share_id}

@app.post("/api/documents/{document_id}/sign")
def sign_document(document_id:int, db:Session=Depends(get_db), user:User=Depends(require_permission(Permission.DOCUMENT_VERSION_CREATE))):
    doc=db.get(Document,document_id)
    if not doc: raise HTTPException(404,"Document not found")
    version=db.scalar(select(DocumentVersion).where(DocumentVersion.document_id==document_id).order_by(DocumentVersion.version.desc()))
    if not version: raise HTTPException(404,"Document has no version")
    try: result=sign_record(db,document_id,version.version,user.id,version.sha256)
    except RuntimeError as e: raise HTTPException(503,str(e))
    audit(db,user,"DOCUMENT_DIGITAL_SIGN","DOCUMENT",document_id,"SUCCESS",json.dumps({"version":version.version,"signed_hash":version.sha256,"signature_id":result["id"]}))
    return {"id":result["id"],"document_id":document_id,"version":version.version,"signer_id":user.id,"signer_email":user.email,"algorithm":result["algorithm"],"signed_hash":version.sha256,"created_at":result["created_at"],"existing":bool(result.get("existing", False))}

@app.get("/api/documents/{document_id}/signatures")
def signatures(document_id:int, db:Session=Depends(get_db), user:User=Depends(require_permission(Permission.DOCUMENT_READ))):
    return [{k:v for k,v in x.items() if k not in {"signature_b64","public_key_pem"}} for x in list_signatures(db,document_id)]

@app.post("/api/documents/{document_id}/signatures/{signature_id}/verify")
def verify_document_signature(document_id:int,signature_id:int,db:Session=Depends(get_db),user:User=Depends(require_permission(Permission.DOCUMENT_VERIFY))):
    sig=db.execute(__import__("sqlalchemy").text("SELECT * FROM document_signatures WHERE id=:i AND document_id=:d"),{"i":signature_id,"d":document_id}).mappings().first()
    if not sig: raise HTTPException(404,"Signature not found")
    version=db.scalar(select(DocumentVersion).where(DocumentVersion.document_id==document_id,DocumentVersion.version==sig["version"]))
    if not version: raise HTTPException(404,"Signed version not found")
    try: verify_signature(sig["signature_b64"],sig["public_key_pem"],version.sha256); ok=version.sha256==sig["signed_hash"]
    except Exception: ok=False
    audit(db,user,"DIGITAL_SIGNATURE_VERIFY","DOCUMENT",document_id,"VERIFIED" if ok else "FAILED",json.dumps({"signature_id":signature_id,"version":sig["version"]}))
    return {"verified":ok,"signature_id":signature_id,"version":sig["version"],"current_bytes_match_signed_hash":version.sha256==sig["signed_hash"]}

@app.get("/api/documents/{document_id}/governance")
def get_governance(document_id:int,db:Session=Depends(get_db),user:User=Depends(require_permission(Permission.DOCUMENT_READ))):
    if not db.get(Document,document_id): raise HTTPException(404,"Document not found")
    return governance(db,document_id)

@app.post("/api/documents/{document_id}/retention")
def retention(document_id:int,body:dict,db:Session=Depends(get_db),user:User=Depends(require_permission(Permission.DOCUMENT_VERSION_CREATE))):
    if not db.get(Document,document_id): raise HTTPException(404,"Document not found")
    try: until=datetime.fromisoformat(str(body.get("retain_until")).replace("Z","+00:00"))
    except Exception: raise HTTPException(400,"retain_until must be an ISO timestamp")
    if until <= datetime.now(timezone.utc): raise HTTPException(400,"Retention date must be in the future")
    row=set_retention(db,document_id,until,str(body.get("reason","Legal/investigative retention requirement")),user.id)
    audit(db,user,"RETENTION_POLICY_SET","DOCUMENT",document_id,"SUCCESS",json.dumps({"retain_until":until.isoformat()}))
    return row

@app.post("/api/documents/{document_id}/legal-hold")
def legal_hold(document_id:int,body:dict,db:Session=Depends(get_db),user:User=Depends(require_permission(Permission.DOCUMENT_VERSION_CREATE))):
    if not db.get(Document,document_id): raise HTTPException(404,"Document not found")
    active=bool(body.get("active",True)); reason=str(body.get("reason","Legal hold requested"))
    row=set_hold(db,document_id,active,reason,user.id)
    audit(db,user,"LEGAL_HOLD_SET" if active else "LEGAL_HOLD_RELEASE","DOCUMENT",document_id,"SUCCESS",json.dumps({"active":active,"reason":reason}))
    return row

@app.get("/api/governance/summary")
def governance_summary(db:Session=Depends(get_db),user:User=Depends(require_permission(Permission.DOCUMENT_READ))):
    return {"active_legal_holds":db.execute(__import__("sqlalchemy").text("SELECT COUNT(*) FROM legal_holds WHERE active=TRUE")).scalar() or 0,
            "retention_policies":db.execute(__import__("sqlalchemy").text("SELECT COUNT(*) FROM retention_policies")).scalar() or 0,
            "active_shares":db.execute(__import__("sqlalchemy").text("SELECT COUNT(*) FROM document_shares WHERE revoked_at IS NULL AND expires_at>NOW()")).scalar() or 0,
            "signatures":db.execute(__import__("sqlalchemy").text("SELECT COUNT(*) FROM document_signatures")).scalar() or 0}

@app.get("/api/documents/{document_id}/forensic-export")
def forensic_export(
    document_id: int,
    include_bytes: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.DOCUMENT_DOWNLOAD)),
):
    """Build a portable integrity-oriented evidence package."""
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    case = db.get(Case, doc.case_id)
    versions = list(db.scalars(select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.version.asc())))
    if not versions:
        raise HTTPException(404, "Document has no evidence versions")
    custody = build_custody_record(db, document_id, verify_bytes=True)
    gov_state = governance(db, document_id)
    sigs = [{k:v for k,v in x.items() if k not in {"signature_b64","public_key_pem"}} for x in list_signatures(db, document_id)]
    audits = [dict(x) for x in db.execute(select(AuditEvent).where((AuditEvent.target_id == str(document_id)) | (AuditEvent.target_id.like(f"{document_id}:%"))).order_by(AuditEvent.created_at.asc())).mappings().all()]
    manifest = {
        "package_type":"KAIRO_FORENSIC_EVIDENCE_PACKAGE","package_version":"1.0",
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "generated_by":{"user_id":user.id,"email":user.email,"role":user.role},
        "document":{"id":doc.id,"document_number":doc.document_number,"title":doc.title,"document_type":doc.document_type,"classification":doc.classification,"case_id":doc.case_id,"current_version":doc.current_version},
        "case":{"id":case.id if case else None,"case_number":case.case_number if case else None,"title":case.title if case else None,"status":case.status if case else None},
        "versions":[{"id":v.id,"version":v.version,"filename":v.original_filename,"content_type":v.content_type,"size_bytes":v.size_bytes,"sha256":v.sha256,"uploaded_by":v.uploaded_by,"created_at":v.created_at.isoformat() if v.created_at else None} for v in versions],
        "custody":custody,"governance":gov_state,"signatures":sigs,"audit_events":audits,"include_bytes":bool(include_bytes)
    }
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as z:
        for name,payload in [("manifest.json",manifest),("case.json",manifest["case"]),("document.json",manifest["document"]),("versions.json",manifest["versions"]),("custody.json",custody),("governance.json",gov_state),("signatures.json",sigs),("audit-events.json",audits)]:
            z.writestr(name,json.dumps(payload,indent=2,default=str))
        if include_bytes:
            for v in versions:
                data=get_bytes(v.object_key); observed=hashlib.sha256(data).hexdigest()
                if observed != v.sha256:
                    raise HTTPException(409,f"Refusing export: version {v.version} failed integrity verification.")
                safe=Path(v.original_filename or f"version-{v.version}").name
                z.writestr(f"evidence/v{v.version}/{safe}",data)
    audit(db,user,"FORENSIC_EXPORT","DOCUMENT",document_id,"SUCCESS",json.dumps({"include_bytes":include_bytes,"versions":len(versions)}))
    return Response(content=buf.getvalue(),media_type="application/zip",headers={"Content-Disposition":f'attachment; filename="{doc.document_number}-forensic-package.zip"'})

@app.get("/api/security/posture")
def security_posture(user: User = Depends(current_user)):
    return {
        "authentication":"JWT","authorization":"RBAC","storage":"MinIO + PostgreSQL metadata","integrity":"SHA-256","custody":"Authorized lifecycle events","trust_ledger":"SHA-256 chained audit events","blockchain":blockchain_status(),"digital_signatures":"RSA-PSS-SHA256","sharing":"Authenticated account-bound, expiring, revocable","governance":"Retention + legal hold","upload_limit_mb":25,"response_hardening":["X-Content-Type-Options","X-Frame-Options","Referrer-Policy","no-store"],"login_rate_limit":{"window_seconds":_LOGIN_WINDOW,"max_attempts":_LOGIN_MAX_ATTEMPTS}
    }

@app.get(
    "/api/audit",
    response_model=list[AuditOut],
)
def audit_events(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(Permission.AUDIT_READ)),
):
    return list(
        db.scalars(
            select(AuditEvent)
            .order_by(AuditEvent.created_at.desc())
            .limit(100)
        )
    )


@app.get("/api/documents/{document_id}/versions/{version_number}/download")
def download_document_version(
    document_id: int, version_number: int, db: Session = Depends(get_db), user: User = Depends(current_user),
):
    """Retrieve one exact immutable version after an integrity check."""
    doc=db.get(Document, document_id)
    if not doc: raise HTTPException(404, "Document not found")
    if not has_permission(user, Permission.DOCUMENT_DOWNLOAD):
        deny(db,user,"DOCUMENT_DOWNLOAD","DOCUMENT_VERSION",f"{document_id}:v{version_number}","Role does not permit document download")
    version=db.scalar(select(DocumentVersion).where(DocumentVersion.document_id==document_id, DocumentVersion.version==version_number))
    if not version: raise HTTPException(404, "Evidence version not found")
    data=get_bytes(version.object_key); observed=hashlib.sha256(data).hexdigest()
    if observed != version.sha256:
        audit(db,user,"DOCUMENT_VERSION_DOWNLOAD","DOCUMENT_VERSION",f"{document_id}:v{version_number}","BLOCKED",json.dumps({"expected":version.sha256,"observed":observed}))
        raise HTTPException(409,"Refusing retrieval: this evidence version failed integrity verification")
    audit(db,user,"DOCUMENT_VERSION_DOWNLOAD","DOCUMENT_VERSION",f"{document_id}:v{version_number}","SUCCESS",json.dumps({"sha256":version.sha256}))
    return Response(content=data,media_type=version.content_type,headers={"Content-Disposition":f'attachment; filename="{version.original_filename}"'})


@app.get("/api/documents/{document_id}/download")
def download_document(
    document_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    # Auditors can inspect metadata and verify integrity, but cannot
    # retrieve restricted document bytes.
    if not has_permission(user, Permission.DOCUMENT_DOWNLOAD):
        deny(
            db,
            user,
            "DOCUMENT_DOWNLOAD",
            "DOCUMENT",
            document_id,
            "Role does not permit document download",
        )

    version = db.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version.desc())
    )

    if not version:
        raise HTTPException(404, "Document has no version")

    data = get_bytes(version.object_key)
    observed = hashlib.sha256(data).hexdigest()
    if observed != version.sha256:
        audit(
            db,
            user,
            "DOCUMENT_VIEW",
            "DOCUMENT",
            doc.id,
            "BLOCKED",
            json.dumps({"version": version.version, "expected": version.sha256, "observed": observed}),
        )
        raise HTTPException(409, "Refusing retrieval: current evidence failed integrity verification")

    audit(
        db,
        user,
        "DOCUMENT_VIEW",
        "DOCUMENT",
        doc.id,
        "SUCCESS",
        f"version={version.version};sha256={observed}",
    )

    return Response(
        content=data,
        media_type=version.content_type,
        headers={
            "Content-Disposition":
                f'inline; filename="{version.original_filename}"'
        },
    )
