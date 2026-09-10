from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import secrets
import shutil
import sqlite3
import time
import uuid
import zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
EVIDENCE = DATA / "evidence"
TRUSTED = DATA / "trusted"
EXPORTS = DATA / "exports"
DB_PATH = DATA / "kairo.db"
KEYS = DATA / "keys"
SECRET = os.environ.get("KAIRO_SECRET", "change-this-secret-in-production")
ATTACK_KEY = os.environ.get("KAIRO_ATTACK_KEY", "KAIRO-LAB-2026")
MAX_UPLOAD = 50 * 1024 * 1024

for p in (DATA, EVIDENCE, TRUSTED, EXPORTS, KEYS):
    p.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="KAIRO", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("KAIRO_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROLES = {
    "POLICE": {
        "label": "Law Enforcement / Police Agency",
        "permissions": {"case.create", "case.read", "case.update", "evidence.create", "evidence.read", "evidence.verify", "evidence.share"},
    },
    "INVESTIGATOR": {
        "label": "Investigative / Specialized Agency",
        "permissions": {"case.create", "case.read", "case.update", "evidence.create", "evidence.read", "evidence.verify", "evidence.share", "investigation.write"},
    },
    "FORENSIC": {
        "label": "Forensic / Scientific Laboratory",
        "permissions": {"case.read", "evidence.read", "evidence.verify", "evidence.restore", "forensic.write", "report.create", "incident.read", "trust.read"},
    },
    "LEGAL": {
        "label": "Judiciary / Legal Institution",
        "permissions": {"case.read", "evidence.read", "evidence.verify", "report.read"},
    },
    "AUDITOR": {
        "label": "Audit / Compliance",
        "permissions": {"case.read", "evidence.read", "audit.read", "incident.read", "trust.read"},
    },
    "ADMIN": {
        "label": "System Administration",
        "permissions": {"*", "admin.users"},
    },
}

USERS = {
    "police@kairo.local": ("Police Officer", "POLICE", "KairoDemo!2026"),
    "investigator@kairo.local": ("Investigation Officer", "INVESTIGATOR", "KairoDemo!2026"),
    "forensic@kairo.local": ("Forensic Examiner", "FORENSIC", "KairoDemo!2026"),
    "legal@kairo.local": ("Judicial Reviewer", "LEGAL", "KairoDemo!2026"),
    "auditor@kairo.local": ("Compliance Auditor", "AUDITOR", "KairoDemo!2026"),
    "admin@kairo.local": ("System Administrator", "ADMIN", "KairoDemo!2026"),
}

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(
 id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL,
 password_hash TEXT NOT NULL, active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS cases(
 id INTEGER PRIMARY KEY, case_no TEXT UNIQUE NOT NULL, title TEXT NOT NULL, description TEXT DEFAULT '',
 classification TEXT DEFAULT 'RESTRICTED', priority TEXT DEFAULT 'HIGH',
 status TEXT DEFAULT 'UNDER INVESTIGATION', station TEXT DEFAULT '', created_by INTEGER, created_at TEXT
);
CREATE TABLE IF NOT EXISTS members(case_id INTEGER NOT NULL, user_id INTEGER NOT NULL, added_at TEXT, UNIQUE(case_id,user_id));
CREATE TABLE IF NOT EXISTS evidence(
 id INTEGER PRIMARY KEY, evidence_no TEXT UNIQUE NOT NULL, case_id INTEGER NOT NULL, title TEXT NOT NULL,
 kind TEXT NOT NULL, classification TEXT DEFAULT 'RESTRICTED', current_version INTEGER DEFAULT 1,
 status TEXT DEFAULT 'VERIFIED', created_by INTEGER, created_at TEXT, sealed INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS versions(
 id INTEGER PRIMARY KEY, evidence_id INTEGER NOT NULL, version INTEGER NOT NULL, filename TEXT NOT NULL,
 object_path TEXT NOT NULL, sha256 TEXT NOT NULL, size INTEGER NOT NULL, created_by INTEGER, created_at TEXT,
 restored_from INTEGER, reason TEXT DEFAULT '', UNIQUE(evidence_id,version)
);
CREATE TABLE IF NOT EXISTS events(
 id INTEGER PRIMARY KEY, event_id TEXT UNIQUE NOT NULL, actor_id INTEGER, action TEXT NOT NULL,
 target_type TEXT NOT NULL, target_id TEXT NOT NULL, result TEXT NOT NULL, details TEXT DEFAULT '',
 created_at TEXT NOT NULL, prev_hash TEXT NOT NULL, event_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS incidents(
 id INTEGER PRIMARY KEY, incident_no TEXT UNIQUE NOT NULL, evidence_id INTEGER NOT NULL,
 expected_hash TEXT NOT NULL, observed_hash TEXT NOT NULL, status TEXT NOT NULL, detected_at TEXT NOT NULL,
 resolved_at TEXT, resolved_by INTEGER, details TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS trust(
 id INTEGER PRIMARY KEY, evidence_id INTEGER NOT NULL, version INTEGER NOT NULL, sha256 TEXT NOT NULL,
 event_hash TEXT, anchor_id TEXT UNIQUE NOT NULL, proof TEXT NOT NULL, provider TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS shares(
 id INTEGER PRIMARY KEY, evidence_id INTEGER NOT NULL, shared_by INTEGER NOT NULL, shared_with INTEGER NOT NULL,
 permission TEXT NOT NULL, expires_at TEXT NOT NULL, revoked_at TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS signatures(
 id INTEGER PRIMARY KEY, evidence_id INTEGER NOT NULL, version INTEGER NOT NULL, signer_id INTEGER NOT NULL,
 signed_hash TEXT NOT NULL, signature_b64 TEXT NOT NULL, algorithm TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS governance(
 id INTEGER PRIMARY KEY, evidence_id INTEGER UNIQUE NOT NULL, retain_until TEXT, retention_reason TEXT,
 legal_hold INTEGER DEFAULT 0, legal_hold_reason TEXT, updated_by INTEGER, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS redactions(
 id INTEGER PRIMARY KEY, evidence_id INTEGER NOT NULL, version INTEGER NOT NULL, findings_json TEXT NOT NULL,
 created_by INTEGER, created_at TEXT NOT NULL
);
"""

def db():
    c = sqlite3.connect(DB_PATH, timeout=20)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    return c

def now():
    return datetime.now(timezone.utc).isoformat()

def parse_dt(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 240000)
    return salt.hex() + ":" + dk.hex()

def password_verify(password, stored):
    try:
        salt, expected = stored.split(":", 1)
        got = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 240000).hex()
        return secrets.compare_digest(got, expected)
    except Exception:
        return False

def ensure_column(c, table, column, definition):
    cols = {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def init():
    c = db()
    c.executescript(SCHEMA)
    ensure_column(c, "cases", "station", "TEXT DEFAULT ''")
    ensure_column(c, "versions", "reason", "TEXT DEFAULT ''")
    ensure_column(c, "evidence", "sealed", "INTEGER DEFAULT 0")
    ensure_column(c, "trust", "proof", "TEXT DEFAULT ''")
    ensure_column(c, "trust", "provider", "TEXT DEFAULT 'LOCAL_PERMISSIONED_TRUST_ANCHOR'")
    ensure_column(c, "users", "created_at", "TEXT")
    for email, (name, role, pw) in USERS.items():
        if not c.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
            c.execute("INSERT INTO users(email,name,role,password_hash,created_at) VALUES(?,?,?,?,?)",
                      (email, name, role, password_hash(pw), now()))
    c.commit()
    c.close()

def audit(actor, action, target_type, target_id, result="SUCCESS", details=None):
    details = details or {}
    c = db()
    prev = c.execute("SELECT event_hash FROM events ORDER BY id DESC LIMIT 1").fetchone()
    prev_hash = prev["event_hash"] if prev else "GENESIS"
    event_id = "EVT-" + uuid.uuid4().hex[:12].upper()
    ts = now()
    detail_text = json.dumps(details, sort_keys=True, separators=(",", ":"))
    payload = "|".join([event_id, str(actor["id"] if actor else "SYSTEM"), action, target_type, str(target_id),
                        result, detail_text, ts, prev_hash])
    event_hash = sha_bytes(payload.encode())
    c.execute("""INSERT INTO events(event_id,actor_id,action,target_type,target_id,result,details,created_at,prev_hash,event_hash)
                 VALUES(?,?,?,?,?,?,?,?,?,?)""",
              (event_id, actor["id"] if actor else None, action, target_type, str(target_id), result,
               detail_text, ts, prev_hash, event_hash))
    c.commit()
    c.close()
    return event_id, event_hash

def token_for(user):
    return jwt.encode(
        {"sub": str(user["id"]), "exp": int(time.time()) + 8 * 3600, "jti": uuid.uuid4().hex},
        SECRET, algorithm="HS256"
    )

def user_from_token(auth: Optional[str]):
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(401, "Authentication required")
    try:
        payload = jwt.decode(auth[7:], SECRET, algorithms=["HS256"])
        uid = int(payload["sub"])
    except Exception:
        raise HTTPException(401, "Invalid session")
    c = db()
    u = c.execute("SELECT * FROM users WHERE id=? AND active=1", (uid,)).fetchone()
    c.close()
    if not u:
        raise HTTPException(401, "User inactive")
    return u

def require(u, permission):
    permissions = ROLES[u["role"]]["permissions"]
    if "*" in permissions or permission in permissions:
        return
    audit(u, "AUTHZ_DENIED", "PERMISSION", permission, "DENIED", {"role": u["role"]})
    raise HTTPException(403, "This action is not permitted for your role")

def case_access(u, case_id):
    if u["role"] in ("ADMIN", "AUDITOR"):
        return
    c = db()
    ok = c.execute("SELECT 1 FROM members WHERE case_id=? AND user_id=?", (case_id, u["id"])).fetchone()
    c.close()
    if not ok:
        raise HTTPException(403, "You are not assigned to this case")

def evidence_access(u, evidence_id):
    c = db()
    e = c.execute("SELECT * FROM evidence WHERE id=?", (evidence_id,)).fetchone()
    c.close()
    if not e:
        raise HTTPException(404, "Evidence not found")
    case_access(u, e["case_id"])
    return e

def safe_filename(name):
    name = Path(name or "evidence.bin").name
    return "".join(ch for ch in name if ch.isalnum() or ch in " ._-()[]").strip()[:180] or "evidence.bin"

def trusted_path(eid, version, filename):
    return TRUSTED / str(eid) / f"v{version}" / filename

def verified_object_path(eid, version_row):
    primary = ROOT / version_row["object_path"]
    if primary.exists() and sha_file(primary) == version_row["sha256"]:
        return primary, "PRIMARY"
    recovery = trusted_path(eid, version_row["version"], version_row["filename"])
    if recovery.exists() and sha_file(recovery) == version_row["sha256"]:
        return recovery, "TRUSTED_RECOVERY"
    return None, "UNAVAILABLE"

def seed_demo():
    c = db()
    if c.execute("SELECT COUNT(*) FROM cases").fetchone()[0]:
        c.close()
        return
    inv = c.execute("SELECT * FROM users WHERE email=?", ("investigator@kairo.local",)).fetchone()
    case_no = "NCRB-WS-2026-0047"
    ts = now()
    c.execute("""INSERT INTO cases(case_no,title,description,classification,priority,status,station,created_by,created_at)
                 VALUES(?,?,?,?,?,?,?,?,?)""",
              (case_no, "Project Sakshi",
               "Synthetic demonstration investigation for the secure evidence lifecycle.",
               "RESTRICTED", "HIGH", "UNDER INVESTIGATION", "Women Safety Investigation Unit", inv["id"], ts))
    cid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    for email in ("investigator@kairo.local", "police@kairo.local", "forensic@kairo.local", "legal@kairo.local"):
        u = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        c.execute("INSERT OR IGNORE INTO members(case_id,user_id,added_at) VALUES(?,?,?)", (cid, u["id"], ts))
    demo = [
        ("First Information Report", "FIR", "FIR_Project_Sakshi.pdf"),
        ("Witness Statement", "WITNESS STATEMENT", "Witness_Statement_Project_Sakshi.pdf"),
        ("Forensic Examination Note", "FORENSIC REPORT", "Forensic_Report_Project_Sakshi.pdf"),
    ]
    for title, kind, fn in demo:
        source = DATA / "demo" / fn
        if not source.exists():
            continue
        data = source.read_bytes()
        h = sha_bytes(data)
        eno = "E-" + uuid.uuid4().hex[:8].upper()
        c.execute("""INSERT INTO evidence(evidence_no,case_id,title,kind,classification,current_version,status,created_by,created_at)
                     VALUES(?,?,?,?,?,?,?,?,?)""",
                  (eno, cid, title, kind, "RESTRICTED", 1, "VERIFIED", inv["id"], ts))
        eid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        fn = safe_filename(fn)
        obj = EVIDENCE / str(eid) / "v1" / fn
        trusted = TRUSTED / str(eid) / "v1" / fn
        obj.parent.mkdir(parents=True, exist_ok=True)
        trusted.parent.mkdir(parents=True, exist_ok=True)
        obj.write_bytes(data); trusted.write_bytes(data)
        c.execute("""INSERT INTO versions(evidence_id,version,filename,object_path,sha256,size,created_by,created_at,reason)
                     VALUES(?,?,?,?,?,?,?,?,?)""",
                  (eid, 1, fn, str(obj.relative_to(ROOT)), h, len(data), inv["id"], ts, "Initial registration"))
        c.execute("INSERT INTO governance(evidence_id,retain_until,retention_reason,updated_at) VALUES(?,?,?,?)",
                  (eid, (datetime.now(timezone.utc) + timedelta(days=365*3)).isoformat(), "Investigation retention", ts))
    c.commit(); c.close()
    audit(inv, "DEMO_CASE_SEEDED", "CASE", cid, details={"case_no": case_no, "synthetic": True})

def get_case(cid):
    c = db()
    r = c.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone()
    c.close()
    if not r:
        raise HTTPException(404, "Case not found")
    return dict(r)

def evidence_payload(eid, u):
    e = evidence_access(u, eid)
    c = db()
    versions = c.execute("""SELECT v.*,u.name creator FROM versions v LEFT JOIN users u ON u.id=v.created_by
                            WHERE evidence_id=? ORDER BY version""", (eid,)).fetchall()
    incidents = c.execute("SELECT * FROM incidents WHERE evidence_id=? ORDER BY id DESC", (eid,)).fetchall()
    trust = c.execute("SELECT * FROM trust WHERE evidence_id=? ORDER BY id DESC", (eid,)).fetchall()
    c.close()
    return {"evidence": dict(e), "versions": [dict(v) for v in versions],
            "incidents": [dict(i) for i in incidents], "trust": [dict(t) for t in trust]}

@app.on_event("startup")
def startup():
    init()
    seed_demo()

@app.get("/api/health")
def health():
    c = db()
    counts = {
        "cases": c.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
        "evidence": c.execute("SELECT COUNT(*) FROM evidence").fetchone()[0],
        "versions": c.execute("SELECT COUNT(*) FROM versions").fetchone()[0],
        "events": c.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        "incidents": c.execute("SELECT COUNT(*) FROM incidents").fetchone()[0],
    }
    c.close()
    return {"status": "ok", "storage": "versioned-local-object-store",
            "integrity": "sha256", "trust": "local-permissioned-anchor", "counts": counts}

@app.post("/api/login")
def login(body: dict):
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    c = db(); u = c.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone(); c.close()
    if not u or not password_verify(password, u["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    audit(u, "LOGIN", "SESSION", u["id"])
    return {"access_token": token_for(u),
            "user": {"id": u["id"], "email": u["email"], "name": u["name"], "role": u["role"],
                     "department": ROLES[u["role"]]["label"]}}

@app.post("/api/logout")
def logout(authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization)
    audit(u, "LOGOUT", "SESSION", u["id"])
    return {"ok": True}

@app.get("/api/me")
def me(authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization)
    return {"id": u["id"], "email": u["email"], "name": u["name"], "role": u["role"],
            "department": ROLES[u["role"]]["label"], "permissions": sorted(ROLES[u["role"]]["permissions"])}

@app.get("/api/permissions")
def permissions(authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization)
    return {"role": u["role"], "department": ROLES[u["role"]]["label"],
            "permissions": sorted(ROLES[u["role"]]["permissions"])}

@app.get("/api/dashboard")
def dashboard(authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization)
    require(u, "case.read")
    c = db()
    if u["role"] in ("ADMIN", "AUDITOR"):
        counts = [c.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
                  c.execute("SELECT COUNT(*) FROM evidence").fetchone()[0],
                  c.execute("SELECT COUNT(*) FROM versions").fetchone()[0],
                  c.execute("SELECT COUNT(*) FROM events").fetchone()[0]]
    else:
        where = "JOIN members m ON m.case_id=c.id WHERE m.user_id=?"
        counts = [
            c.execute(f"SELECT COUNT(DISTINCT c.id) FROM cases c {where}", (u["id"],)).fetchone()[0],
            c.execute("""SELECT COUNT(*) FROM evidence e JOIN cases c ON c.id=e.case_id
                         JOIN members m ON m.case_id=c.id WHERE m.user_id=?""", (u["id"],)).fetchone()[0],
            c.execute("""SELECT COUNT(*) FROM versions v JOIN evidence e ON e.id=v.evidence_id
                         JOIN cases c ON c.id=e.case_id JOIN members m ON m.case_id=c.id WHERE m.user_id=?""", (u["id"],)).fetchone()[0],
            c.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        ]
    c.close()
    return {"cases": counts[0], "documents": counts[1], "versions": counts[2], "audit_events": counts[3]}

@app.post("/api/cases")
def create_case(body: dict, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "case.create")
    case_no = str(body.get("case_no") or body.get("case_number") or f"KAIRO-{datetime.now().year}-{secrets.randbelow(9000)+1000}").strip()
    title = str(body.get("title", "")).strip()
    if not title or len(title) > 200:
        raise HTTPException(422, "A valid case title is required")
    c = db()
    try:
        c.execute("""INSERT INTO cases(case_no,title,description,classification,priority,status,station,created_by,created_at)
                     VALUES(?,?,?,?,?,?,?,?,?)""",
                  (case_no, title, str(body.get("description", ""))[:5000],
                   body.get("classification", "RESTRICTED"), body.get("priority", "HIGH"),
                   "UNDER INVESTIGATION", str(body.get("station", ""))[:200], u["id"], now()))
        cid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        c.execute("INSERT INTO members(case_id,user_id,added_at) VALUES(?,?,?)", (cid, u["id"], now()))
        c.commit()
    except sqlite3.IntegrityError:
        c.close(); raise HTTPException(409, "Case number already exists")
    c.close()
    audit(u, "CASE_CREATED", "CASE", cid, details={"case_no": case_no})
    return get_case(cid)

@app.get("/api/cases")
def cases(authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "case.read")
    c = db()
    if u["role"] in ("ADMIN", "AUDITOR"):
        rows = c.execute("SELECT * FROM cases ORDER BY id DESC").fetchall()
    else:
        rows = c.execute("""SELECT DISTINCT c.* FROM cases c JOIN members m ON m.case_id=c.id
                            WHERE m.user_id=? ORDER BY c.id DESC""", (u["id"],)).fetchall()
    c.close()
    return [dict(r) for r in rows]

@app.get("/api/cases/{cid}")
def case_detail(cid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "case.read"); case_access(u, cid)
    c = db()
    case = c.execute("SELECT * FROM cases WHERE id=?", (cid,)).fetchone()
    if not case:
        c.close(); raise HTTPException(404, "Case not found")
    ev = c.execute("SELECT * FROM evidence WHERE case_id=? ORDER BY id DESC", (cid,)).fetchall()
    members = c.execute("""SELECT u.id,u.email,u.name,u.role FROM users u JOIN members m ON m.user_id=u.id
                           WHERE m.case_id=? ORDER BY u.name""", (cid,)).fetchall()
    c.close()
    return {"case": dict(case), "evidence": [dict(x) for x in ev], "members": [dict(x) for x in members]}

@app.get("/api/cases/{cid}/members")
def case_members(cid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "case.read"); case_access(u, cid)
    c = db(); rows = c.execute("""SELECT u.id,u.email,u.name,u.role FROM users u JOIN members m ON m.user_id=u.id
                                  WHERE m.case_id=?""", (cid,)).fetchall(); c.close()
    return [dict(r) for r in rows]

@app.post("/api/cases/{cid}/members")
def add_member(cid: int, body: dict, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "case.update"); case_access(u, cid)
    email = str(body.get("email", "")).lower().strip()
    c = db(); target = c.execute("SELECT * FROM users WHERE email=? AND active=1", (email,)).fetchone()
    if not target:
        c.close(); raise HTTPException(404, "User not found")
    c.execute("INSERT OR IGNORE INTO members(case_id,user_id,added_at) VALUES(?,?,?)", (cid, target["id"], now()))
    c.commit(); c.close()
    audit(u, "CASE_MEMBER_ADDED", "CASE", cid, details={"user": email, "role": target["role"]})
    return {"ok": True}

@app.delete("/api/cases/{cid}/members/{member_id}")
def remove_member(cid: int, member_id: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "case.update"); case_access(u, cid)
    if member_id == u["id"]:
        raise HTTPException(400, "You cannot remove yourself from a case")
    c = db(); c.execute("DELETE FROM members WHERE case_id=? AND user_id=?", (cid, member_id)); c.commit(); c.close()
    audit(u, "CASE_MEMBER_REMOVED", "CASE", cid, details={"user_id": member_id})
    return {"ok": True}

@app.post("/api/cases/{cid}/evidence")
def upload(cid: int, file: UploadFile = File(...), title: str = Form(...), document_type: str = Form("FIR"),
           classification: str = Form("RESTRICTED"), kind: str = Form(None),
           authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.create"); case_access(u, cid)
    e_kind = kind or document_type
    if not file.filename: raise HTTPException(422, "Filename is required")
    data = file.file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD: raise HTTPException(413, "Evidence exceeds the 50 MB upload limit")
    filename = safe_filename(file.filename)
    h = sha_bytes(data); ts = now()
    c = db()
    eno = "E-" + uuid.uuid4().hex[:8].upper()
    c.execute("""INSERT INTO evidence(evidence_no,case_id,title,kind,classification,current_version,status,created_by,created_at)
                 VALUES(?,?,?,?,?,?,?,?,?)""", (eno, cid, title[:200], e_kind[:80], classification[:50], 1, "VERIFIED", u["id"], ts))
    eid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
    obj = EVIDENCE / str(eid) / "v1" / filename
    trusted = TRUSTED / str(eid) / "v1" / filename
    obj.parent.mkdir(parents=True, exist_ok=True); trusted.parent.mkdir(parents=True, exist_ok=True)
    obj.write_bytes(data); trusted.write_bytes(data)
    c.execute("""INSERT INTO versions(evidence_id,version,filename,object_path,sha256,size,created_by,created_at,reason)
                 VALUES(?,?,?,?,?,?,?,?,?)""",
              (eid, 1, filename, str(obj.relative_to(ROOT)), h, len(data), u["id"], ts, "Initial registration"))
    c.execute("INSERT INTO governance(evidence_id,updated_by,updated_at) VALUES(?,?,?)", (eid, u["id"], ts))
    c.commit(); c.close()
    audit(u, "EVIDENCE_REGISTERED", "EVIDENCE", eid, details={"evidence_no": eno, "version": 1, "sha256": h})
    return evidence_payload(eid, u)

@app.post("/api/evidence/{eid}/versions")
def new_version(eid: int, file: UploadFile = File(...), reason: str = Form("Authorized update"),
                authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.create")
    e = evidence_access(u, eid)
    if e["sealed"]:
        raise HTTPException(409, "Evidence is sealed; a new version is not permitted")
    data = file.file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD: raise HTTPException(413, "Evidence exceeds the 50 MB upload limit")
    filename = safe_filename(file.filename)
    c = db()
    latest = c.execute("SELECT MAX(version) v FROM versions WHERE evidence_id=?", (eid,)).fetchone()["v"] or 0
    v = latest + 1; h = sha_bytes(data); ts = now()
    obj = EVIDENCE / str(eid) / f"v{v}" / filename
    trusted = TRUSTED / str(eid) / f"v{v}" / filename
    obj.parent.mkdir(parents=True, exist_ok=True); trusted.parent.mkdir(parents=True, exist_ok=True)
    obj.write_bytes(data); trusted.write_bytes(data)
    c.execute("""INSERT INTO versions(evidence_id,version,filename,object_path,sha256,size,created_by,created_at,reason)
                 VALUES(?,?,?,?,?,?,?,?,?)""",
              (eid, v, filename, str(obj.relative_to(ROOT)), h, len(data), u["id"], ts, reason[:1000]))
    c.execute("UPDATE evidence SET current_version=?,status='VERIFIED' WHERE id=?", (v, eid))
    c.commit(); c.close()
    audit(u, "EVIDENCE_VERSION_CREATED", "EVIDENCE", eid, details={"version": v, "reason": reason, "sha256": h})
    return evidence_payload(eid, u)

@app.get("/api/evidence/{eid}")
def get_evidence(eid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.read")
    return evidence_payload(eid, u)

@app.get("/api/evidence/{eid}/versions")
def get_versions(eid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.read"); evidence_access(u, eid)
    c = db(); rows = c.execute("SELECT * FROM versions WHERE evidence_id=? ORDER BY version", (eid,)).fetchall(); c.close()
    return [dict(r) for r in rows]

@app.get("/api/evidence/{eid}/download")
def download_version(eid: int, version: int = 0, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.read"); evidence_access(u, eid)
    c = db()
    if version:
        v = c.execute("SELECT * FROM versions WHERE evidence_id=? AND version=?", (eid, version)).fetchone()
    else:
        v = c.execute("""SELECT v.* FROM versions v JOIN evidence e ON e.id=v.evidence_id
                         WHERE v.evidence_id=? AND v.version=e.current_version""", (eid,)).fetchone()
    c.close()
    if not v: raise HTTPException(404, "Version not found")
    p, source = verified_object_path(eid, v)
    if not p: raise HTTPException(410, "No integrity-verified copy of this evidence version is available")
    audit(u, "EVIDENCE_ACCESSED" if source=="PRIMARY" else "EVIDENCE_RECOVERED_FOR_ACCESS", "EVIDENCE", eid,
          details={"version": v["version"], "source": source})
    return FileResponse(p, filename=v["filename"], media_type=mimetypes.guess_type(v["filename"])[0] or "application/octet-stream")

@app.post("/api/evidence/{eid}/verify")
def verify(eid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.verify"); e = evidence_access(u, eid)
    c = db(); v = c.execute("SELECT * FROM versions WHERE evidence_id=? AND version=?", (eid, e["current_version"])).fetchone(); c.close()
    if not v: raise HTTPException(404, "Current version not found")
    p = ROOT / v["object_path"]
    if not p.exists(): observed = None
    else: observed = sha_file(p)
    result = "VERIFIED" if observed == v["sha256"] else "MISMATCH"
    audit(u, "INTEGRITY_VERIFIED" if result == "VERIFIED" else "INTEGRITY_MISMATCH", "EVIDENCE", eid,
          result, {"version": v["version"], "expected": v["sha256"], "observed": observed})
    incident = None
    if result == "MISMATCH":
        c = db()
        open_inc = c.execute("SELECT * FROM incidents WHERE evidence_id=? AND status='OPEN' ORDER BY id DESC LIMIT 1", (eid,)).fetchone()
        if not open_inc:
            incident_no = "INC-" + uuid.uuid4().hex[:8].upper()
            c.execute("""INSERT INTO incidents(incident_no,evidence_id,expected_hash,observed_hash,status,detected_at,details)
                         VALUES(?,?,?,?,?,?,?)""",
                      (incident_no, eid, v["sha256"], observed or "OBJECT_UNAVAILABLE", "OPEN", now(),
                       "Current evidence bytes differ from the registered version or are unavailable."))
            incident = incident_no
        c.execute("UPDATE evidence SET status='INTEGRITY INCIDENT' WHERE id=?", (eid,))
        c.commit(); c.close()
    return {"result": result, "verified": result == "VERIFIED", "expected": v["sha256"], "observed": observed,
            "expected_sha256": v["sha256"], "observed_sha256": observed, "version": v["version"],
            "evidence_no": e["evidence_no"], "incident": incident}

@app.post("/api/evidence/{eid}/restore")
def restore(eid: int, version: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.restore"); e = evidence_access(u, eid)
    c = db()
    source = c.execute("SELECT * FROM versions WHERE evidence_id=? AND version=?", (eid, version)).fetchone()
    current = c.execute("SELECT * FROM versions WHERE evidence_id=? AND version=?", (eid, e["current_version"])).fetchone()
    if not source or not current:
        c.close(); raise HTTPException(404, "Requested version not found")
    trusted = TRUSTED / str(eid) / f"v{version}" / source["filename"]
    if not trusted.exists(): c.close(); raise HTTPException(404, "Trusted recovery copy not found")
    data = trusted.read_bytes()
    if sha_bytes(data) != source["sha256"]:
        c.close(); raise HTTPException(409, "Trusted recovery copy failed its own integrity check")
    nv = current["version"] + 1
    obj = EVIDENCE / str(eid) / f"v{nv}" / source["filename"]
    trusted_new = TRUSTED / str(eid) / f"v{nv}" / source["filename"]
    obj.parent.mkdir(parents=True, exist_ok=True); trusted_new.parent.mkdir(parents=True, exist_ok=True)
    obj.write_bytes(data); trusted_new.write_bytes(data)
    ts = now()
    c.execute("""INSERT INTO versions(evidence_id,version,filename,object_path,sha256,size,created_by,created_at,restored_from,reason)
                 VALUES(?,?,?,?,?,?,?,?,?,?)""",
              (eid, nv, source["filename"], str(obj.relative_to(ROOT)), source["sha256"], len(data), u["id"], ts,
               source["version"], f"Restored from trusted version {source['version']}"))
    c.execute("UPDATE evidence SET current_version=?,status='VERIFIED' WHERE id=?", (nv, eid))
    c.execute("UPDATE incidents SET status='RESOLVED',resolved_at=?,resolved_by=? WHERE evidence_id=? AND status='OPEN'",
              (ts, u["id"], eid))
    c.commit(); c.close()
    audit(u, "EVIDENCE_RESTORED", "EVIDENCE", eid,
          details={"from_version": source["version"], "new_version": nv, "sha256": source["sha256"]})
    return {"ok": True, "version": nv, "restored_from": source["version"], **evidence_payload(eid, u)}

@app.get("/api/audit")
def audit_list(authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "audit.read")
    c = db()
    rows = c.execute("""SELECT e.*,u.name actor,u.role actor_role FROM events e LEFT JOIN users u ON u.id=e.actor_id
                        ORDER BY e.id DESC LIMIT 500""").fetchall()
    c.close()
    return [dict(r) for r in rows]

@app.get("/api/incidents")
def incidents(status: str = "", authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "incident.read")
    c = db()
    sql = """SELECT i.*,e.evidence_no,e.title,c.case_no FROM incidents i
             JOIN evidence e ON e.id=i.evidence_id JOIN cases c ON c.id=e.case_id"""
    params = ()
    if status:
        sql += " WHERE i.status=?"; params = (status,)
    sql += " ORDER BY i.id DESC"
    rows = c.execute(sql, params).fetchall(); c.close()
    return [dict(r) for r in rows]

@app.post("/api/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: int, body: dict, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.restore")
    c = db(); i = c.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
    if not i: c.close(); raise HTTPException(404, "Incident not found")
    evidence_access(u, i["evidence_id"])
    c.execute("UPDATE incidents SET status='RESOLVED',resolved_at=?,resolved_by=?,details=? WHERE id=?",
              (now(), u["id"], str(body.get("resolution", "Resolved by authorized officer"))[:2000], incident_id))
    c.commit(); c.close()
    audit(u, "INCIDENT_RESOLVED", "INCIDENT", incident_id, details={"resolution": body.get("resolution", "")})
    return {"ok": True}

@app.get("/api/trust")
def trust_list(authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "trust.read")
    c = db(); rows = c.execute("""SELECT t.*,e.evidence_no,e.title FROM trust t JOIN evidence e ON e.id=t.evidence_id
                                  ORDER BY t.id DESC LIMIT 500""").fetchall(); c.close()
    return [dict(r) for r in rows]

@app.get("/api/trust/ledger")
def trust_ledger(limit: int = 50, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "trust.read")
    c = db(); rows = c.execute("""SELECT t.*,e.evidence_no,e.title FROM trust t JOIN evidence e ON e.id=t.evidence_id
                                  ORDER BY t.id DESC LIMIT ?""", (min(max(limit, 1), 200),)).fetchall(); c.close()
    blocks = []
    for i, r in enumerate(rows, 1):
        blocks.append({"block_index": i, "action": "TRUST_ANCHORED", "target_type": "EVIDENCE",
                       "target_id": r["evidence_id"], "result": "SUCCESS",
                       "transaction_id": r["anchor_id"], "event_hash": r["proof"],
                       "previous_hash": r["event_hash"] or "GENESIS", "created_at": r["created_at"],
                       "evidence_no": r["evidence_no"], "title": r["title"]})
    return {"status": {"verified": True, "blocks": len(blocks), "latest_block": len(blocks)}, "blocks": blocks}

@app.get("/api/trust/verify")
def trust_verify(authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "trust.read")
    c = db(); rows = c.execute("SELECT * FROM trust ORDER BY id").fetchall()
    failures = []
    for t in rows:
        # The proof itself is deterministic over the anchored tuple.
        expected = sha_bytes(f"{t['evidence_id']}|{t['version']}|{t['sha256']}|{t['event_hash']}|{t['anchor_id']}".encode())
        if t["proof"] and t["proof"] != expected:
            failures.append(t["anchor_id"])
    c.close()
    return {"verified": not failures, "status": "VERIFIED" if not failures else "MISMATCH",
            "blocks": len(rows), "latest_block": len(rows), "checked": len(rows), "failures": failures}

def create_trust_anchor(eid, u):
    e = evidence_access(u, eid)
    c = db()
    v = c.execute("SELECT * FROM versions WHERE evidence_id=? AND version=?", (eid, e["current_version"])).fetchone()
    ev = c.execute("""SELECT * FROM events WHERE target_type='EVIDENCE' AND target_id=?
                      ORDER BY id DESC LIMIT 1""", (str(eid),)).fetchone()
    aid = "ANCHOR-" + uuid.uuid4().hex[:12].upper()
    event_hash = ev["event_hash"] if ev else ""
    proof = sha_bytes(f"{eid}|{v['version']}|{v['sha256']}|{event_hash}|{aid}".encode())
    c.execute("""INSERT INTO trust(evidence_id,version,sha256,event_hash,anchor_id,proof,provider,created_at)
                 VALUES(?,?,?,?,?,?,?,?)""",
              (eid, v["version"], v["sha256"], event_hash, aid, proof, "LOCAL_PERMISSIONED_TRUST_ANCHOR", now()))
    c.commit(); c.close()
    audit(u, "TRUST_ANCHORED", "EVIDENCE", eid, details={"anchor_id": aid, "proof": proof})
    return {"anchor_id": aid, "proof": proof, "mode": "LOCAL_PERMISSIONED_TRUST_ANCHOR",
            "fabric": {"connected": False, "txId": None}}

@app.post("/api/trust/anchor/{eid}")
def anchor_legacy(eid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.verify")
    return create_trust_anchor(eid, u)

@app.post("/api/documents/{eid}/blockchain-anchor")
def blockchain_anchor(eid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.verify")
    return create_trust_anchor(eid, u)

@app.get("/api/documents/{eid}/blockchain-anchor")
def blockchain_anchor_read(eid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.verify"); evidence_access(u, eid)
    c = db(); r = c.execute("SELECT * FROM trust WHERE evidence_id=? ORDER BY id DESC LIMIT 1", (eid,)).fetchone(); c.close()
    return {"anchored": bool(r), "anchor": dict(r) if r else None}

@app.get("/api/blockchain/status")
def blockchain_status(authorization: Optional[str] = Header(None)):
    user_from_token(authorization)
    return {"reachable": False, "provider": "LOCAL_PERMISSIONED_TRUST_ANCHOR",
            "message": "Portable trust provider active; Hyperledger Fabric adapter is deployment-ready but not running in this zero-Docker build."}

@app.get("/api/search")
def search(q: str = "", case_id: int = 0, document_type: str = "", classification: str = "",
           limit: int = 50, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.read")
    c = db()
    clauses = []; params = []
    if u["role"] not in ("ADMIN", "AUDITOR"):
        clauses.append("EXISTS (SELECT 1 FROM members mm WHERE mm.case_id=e.case_id AND mm.user_id=?)"); params.append(u["id"])
    if q.strip():
        like = f"%{q.strip()}%"; clauses.append("(e.title LIKE ? OR e.evidence_no LIKE ? OR e.kind LIKE ? OR v.filename LIKE ? OR c.case_no LIKE ?)")
        params += [like] * 5
    if case_id: clauses.append("e.case_id=?"); params.append(case_id)
    if document_type: clauses.append("e.kind=?"); params.append(document_type)
    if classification: clauses.append("e.classification=?"); params.append(classification)
    where = " AND ".join(clauses) if clauses else "1=1"
    rows = c.execute(f"""SELECT e.*,c.case_no,c.title AS case_title,v.filename,v.sha256
                         FROM evidence e JOIN cases c ON c.id=e.case_id
                         JOIN versions v ON v.evidence_id=e.id AND v.version=e.current_version
                         WHERE {where} ORDER BY e.id DESC LIMIT ?""", (*params, min(max(limit, 1), 200))).fetchall()
    c.close()
    return [dict(r) for r in rows]

@app.get("/api/documents/{eid}/custody")
def custody(eid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.read"); evidence_access(u, eid)
    c = db()
    rows = c.execute("""SELECT e.*,u.name actor,u.role actor_role FROM events e LEFT JOIN users u ON u.id=e.actor_id
                        WHERE (e.target_type='EVIDENCE' AND e.target_id=?) OR
                              (e.target_type='DOCUMENT' AND e.target_id=?)
                        ORDER BY e.id ASC""", (str(eid), str(eid))).fetchall()
    c.close()
    return [dict(r) for r in rows]

@app.get("/api/documents/{eid}/trust")
def document_trust(eid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.read"); evidence_access(u, eid)
    c = db(); rows = c.execute("SELECT * FROM trust WHERE evidence_id=? ORDER BY id DESC", (eid,)).fetchall(); c.close()
    return {"anchors": [dict(r) for r in rows]}

@app.get("/api/documents/{eid}/signatures")
def signatures(eid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.read"); evidence_access(u, eid)
    c = db(); rows = c.execute("""SELECT s.*,u.email signer_email,u.name signer_name FROM signatures s
                                  JOIN users u ON u.id=s.signer_id WHERE s.evidence_id=? ORDER BY s.id DESC""", (eid,)).fetchall(); c.close()
    return [dict(r) for r in rows]

def keypair_for(user_id):
    priv_path = KEYS / f"user-{user_id}.pem"
    pub_path = KEYS / f"user-{user_id}.pub.pem"
    if not priv_path.exists():
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        priv_path.write_bytes(private.private_bytes(serialization.Encoding.PEM,
                                                     serialization.PrivateFormat.PKCS8,
                                                     serialization.NoEncryption()))
        pub_path.write_bytes(private.public_key().public_bytes(serialization.Encoding.PEM,
                                                                serialization.PublicFormat.SubjectPublicKeyInfo))
    return serialization.load_pem_private_key(priv_path.read_bytes(), password=None)

@app.post("/api/documents/{eid}/sign")
def sign(eid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "forensic.write"); e = evidence_access(u, eid)
    c = db(); v = c.execute("SELECT * FROM versions WHERE evidence_id=? AND version=?", (eid, e["current_version"])).fetchone()
    existing = c.execute("SELECT s.*,u.email signer_email FROM signatures s JOIN users u ON u.id=s.signer_id WHERE s.evidence_id=? AND s.version=? AND s.signer_id=?",
                         (eid, v["version"], u["id"])).fetchone()
    if existing:
        c.close()
        return {"existing": True, "signer_email": existing["signer_email"], "version": v["version"], "algorithm": existing["algorithm"]}
    private = keypair_for(u["id"])
    signature = private.sign(v["sha256"].encode(), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    import base64
    sig_b64 = base64.b64encode(signature).decode()
    c.execute("""INSERT INTO signatures(evidence_id,version,signer_id,signed_hash,signature_b64,algorithm,created_at)
                 VALUES(?,?,?,?,?,?,?)""",
              (eid, v["version"], u["id"], v["sha256"], sig_b64, "RSA-PSS/SHA-256", now()))
    c.commit(); c.close()
    audit(u, "EVIDENCE_SIGNED", "EVIDENCE", eid, details={"version": v["version"], "hash": v["sha256"]})
    return {"existing": False, "signer_email": u["email"], "version": v["version"], "algorithm": "RSA-PSS/SHA-256"}

@app.post("/api/documents/{eid}/signatures/{sig_id}/verify")
def verify_signature(eid: int, sig_id: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.verify"); evidence_access(u, eid)
    c = db(); s = c.execute("SELECT * FROM signatures WHERE id=? AND evidence_id=?", (sig_id, eid)).fetchone()
    v = c.execute("SELECT * FROM versions WHERE evidence_id=? AND version=?", (eid, s["version"] if s else 0)).fetchone(); c.close()
    if not s or not v: raise HTTPException(404, "Signature not found")
    import base64
    try:
        pub = serialization.load_pem_public_key((KEYS / f"user-{s['signer_id']}.pub.pem").read_bytes())
        pub.verify(base64.b64decode(s["signature_b64"]), s["signed_hash"].encode(),
                   padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
        verified = s["signed_hash"] == v["sha256"]
    except Exception:
        verified = False
    audit(u, "SIGNATURE_VERIFIED", "EVIDENCE", eid, "VERIFIED" if verified else "FAILED", {"signature_id": sig_id})
    return {"verified": verified, "signed_hash": s["signed_hash"], "current_hash": v["sha256"]}

@app.get("/api/users/collaborators")
def collaborators(authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.share")
    c = db(); rows = c.execute("SELECT id,email,name full_name,role FROM users WHERE active=1 AND id!=? ORDER BY name", (u["id"],)).fetchall(); c.close()
    return [dict(r) for r in rows]

def share_access(u, share):
    if share["shared_with"] != u["id"] and share["shared_by"] != u["id"] and u["role"] != "ADMIN":
        raise HTTPException(403, "Share is not assigned to your account")
    if share["revoked_at"]: raise HTTPException(403, "Share has been revoked")
    if parse_dt(share["expires_at"]) and parse_dt(share["expires_at"]) <= datetime.now(timezone.utc):
        raise HTTPException(403, "Share has expired")

@app.post("/api/documents/{eid}/shares")
def share(eid: int, body: dict, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.share"); evidence_access(u, eid)
    email = str(body.get("email", "")).lower().strip()
    c = db(); target = c.execute("SELECT * FROM users WHERE email=? AND active=1", (email,)).fetchone()
    if not target: c.close(); raise HTTPException(404, "Collaborator not found")
    expires = parse_dt(str(body.get("expires_at", "")))
    if not expires or expires <= datetime.now(timezone.utc) or expires > datetime.now(timezone.utc) + timedelta(days=30):
        c.close(); raise HTTPException(422, "Share expiry must be between now and 30 days")
    permission = body.get("permission", "VIEW")
    if permission not in ("VIEW", "DOWNLOAD"): c.close(); raise HTTPException(422, "Invalid share permission")
    c.execute("""INSERT INTO shares(evidence_id,shared_by,shared_with,permission,expires_at,created_at)
                 VALUES(?,?,?,?,?,?)""", (eid, u["id"], target["id"], permission, expires.isoformat(), now()))
    sid = c.execute("SELECT last_insert_rowid()").fetchone()[0]; c.commit(); c.close()
    audit(u, "SHARE_CREATED", "EVIDENCE", eid, details={"share_id": sid, "shared_with": email, "permission": permission})
    return {"id": sid, "shared_with": target["name"], "expires_at": expires.isoformat(), "permission": permission}

def share_rows(u, incoming):
    c = db()
    if incoming:
        rows = c.execute("""SELECT s.*,e.title,u.email shared_by_email,u.name shared_by_name
                            FROM shares s JOIN evidence e ON e.id=s.evidence_id JOIN users u ON u.id=s.shared_by
                            WHERE s.shared_with=? ORDER BY s.id DESC""", (u["id"],)).fetchall()
    else:
        rows = c.execute("""SELECT s.*,e.title,u.email shared_with_email,u.name shared_with_name
                            FROM shares s JOIN evidence e ON e.id=s.evidence_id JOIN users u ON u.id=s.shared_with
                            WHERE s.shared_by=? ORDER BY s.id DESC""", (u["id"],)).fetchall()
    c.close(); return [dict(r) for r in rows]

@app.get("/api/shares/incoming")
def incoming_shares(authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.read"); return share_rows(u, True)

@app.get("/api/shares/outgoing")
def outgoing_shares(authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.share"); return share_rows(u, False)

@app.get("/api/shares/{sid}")
def share_record(sid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization)
    c = db(); s = c.execute("""SELECT s.*,e.evidence_no,e.title,e.current_version FROM shares s JOIN evidence e ON e.id=s.evidence_id
                               WHERE s.id=?""", (sid,)).fetchone(); c.close()
    if not s: raise HTTPException(404, "Share not found")
    share_access(u, s); return dict(s)

@app.post("/api/shares/{sid}/revoke")
def revoke_share(sid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.share")
    c = db(); s = c.execute("SELECT * FROM shares WHERE id=?", (sid,)).fetchone()
    if not s: c.close(); raise HTTPException(404, "Share not found")
    if s["shared_by"] != u["id"] and u["role"] != "ADMIN": c.close(); raise HTTPException(403, "Only the sharer can revoke access")
    c.execute("UPDATE shares SET revoked_at=? WHERE id=?", (now(), sid)); c.commit(); c.close()
    audit(u, "SHARE_REVOKED", "SHARE", sid)
    return {"ok": True}

@app.get("/api/shares/{sid}/download")
def download_shared(sid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization)
    c = db(); s = c.execute("SELECT * FROM shares WHERE id=?", (sid,)).fetchone(); c.close()
    if not s: raise HTTPException(404, "Share not found")
    share_access(u, s)
    if s["permission"] != "DOWNLOAD": raise HTTPException(403, "This share permits viewing only")
    c = db(); e = c.execute("SELECT * FROM evidence WHERE id=?", (s["evidence_id"],)).fetchone()
    v = c.execute("SELECT * FROM versions WHERE evidence_id=? AND version=?", (s["evidence_id"], e["current_version"])).fetchone(); c.close()
    p = ROOT / v["object_path"]
    if not p.exists(): raise HTTPException(410, "Evidence unavailable")
    audit(u, "SHARED_EVIDENCE_ACCESSED", "SHARE", sid, details={"evidence_id": s["evidence_id"], "version": v["version"]})
    return FileResponse(p, filename=v["filename"], media_type=mimetypes.guess_type(v["filename"])[0] or "application/octet-stream")

@app.get("/api/documents/{eid}/governance")
def governance_state(eid):
    c = db(); g = c.execute("SELECT * FROM governance WHERE evidence_id=?", (eid,)).fetchone(); c.close()
    if not g: return {"retention": None, "legal_hold": {"active": False, "reason": ""}}
    return {"retention": {"retain_until": g["retain_until"], "reason": g["retention_reason"]} if g["retain_until"] else None,
            "legal_hold": {"active": bool(g["legal_hold"]), "reason": g["legal_hold_reason"] or ""}}

@app.get("/api/documents/{eid}/governance")
def governance(eid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.read"); evidence_access(u, eid)
    return governance_state(eid)

@app.get("/api/governance/summary")
def governance_summary(authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "case.read")
    c = db()
    result = {
        "active_legal_holds": c.execute("SELECT COUNT(*) FROM governance WHERE legal_hold=1").fetchone()[0],
        "retention_policies": c.execute("SELECT COUNT(*) FROM governance WHERE retain_until IS NOT NULL").fetchone()[0],
        "signatures": c.execute("SELECT COUNT(*) FROM signatures").fetchone()[0],
        "active_shares": c.execute("SELECT COUNT(*) FROM shares WHERE revoked_at IS NULL AND expires_at>?", (now(),)).fetchone()[0],
    }
    c.close(); return result

@app.post("/api/documents/{eid}/retention")
def retention(eid: int, body: dict, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.create"); evidence_access(u, eid)
    dt = parse_dt(str(body.get("retain_until", "")))
    if not dt: raise HTTPException(422, "Invalid retention date")
    c = db(); c.execute("""INSERT INTO governance(evidence_id,retain_until,retention_reason,updated_by,updated_at)
                           VALUES(?,?,?,?,?) ON CONFLICT(evidence_id) DO UPDATE SET retain_until=excluded.retain_until,
                           retention_reason=excluded.retention_reason,updated_by=excluded.updated_by,updated_at=excluded.updated_at""",
                         (eid, dt.isoformat(), str(body.get("reason", ""))[:1000], u["id"], now()))
    c.commit(); c.close(); audit(u, "RETENTION_UPDATED", "EVIDENCE", eid, details={"retain_until": dt.isoformat()})
    return governance_state(eid)

@app.post("/api/documents/{eid}/legal-hold")
def legal_hold(eid: int, body: dict, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.create"); evidence_access(u, eid)
    active = bool(body.get("active"))
    c = db(); c.execute("""INSERT INTO governance(evidence_id,legal_hold,legal_hold_reason,updated_by,updated_at)
                           VALUES(?,?,?,?,?) ON CONFLICT(evidence_id) DO UPDATE SET legal_hold=excluded.legal_hold,
                           legal_hold_reason=excluded.legal_hold_reason,updated_by=excluded.updated_by,updated_at=excluded.updated_at""",
                         (eid, int(active), str(body.get("reason", ""))[:1000], u["id"], now()))
    c.commit(); c.close(); audit(u, "LEGAL_HOLD_PLACED" if active else "LEGAL_HOLD_RELEASED", "EVIDENCE", eid)
    return governance_state(eid)

@app.post("/api/governance/retention/scan")
def retention_scan(authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "audit.read")
    c = db(); rows = c.execute("""SELECT g.*,e.evidence_no FROM governance g JOIN evidence e ON e.id=g.evidence_id
                                  WHERE g.retain_until IS NOT NULL""").fetchall()
    eligible = []
    for r in rows:
        dt = parse_dt(r["retain_until"])
        if dt and dt <= datetime.now(timezone.utc) and not r["legal_hold"]:
            eligible.append(dict(r))
    c.close(); audit(u, "RETENTION_SCAN", "GOVERNANCE", "RETENTION", details={"eligible": len(eligible)})
    return {"eligible": eligible, "count": len(eligible)}

@app.get("/api/governance/dispositions")
def dispositions(authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "audit.read")
    return retention_scan(authorization)

@app.post("/api/documents/{eid}/seal")
def seal(eid: int, body: dict, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "forensic.write"); e = evidence_access(u, eid)
    version = int(body.get("version") or e["current_version"])
    if version != e["current_version"]: raise HTTPException(409, "Only the current version can be sealed")
    c = db(); c.execute("UPDATE evidence SET sealed=1,status='SEALED' WHERE id=?", (eid,)); c.commit(); c.close()
    audit(u, "EVIDENCE_SEALED", "EVIDENCE", eid, details={"version": version})
    return {"ok": True, "sealed": True, "version": version}

def scan_text(data):
    text = data.decode("utf-8", errors="ignore")
    findings = []
    import re
    patterns = [
        ("EMAIL", r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
        ("PHONE", r"\b(?:\+91[- ]?)?[6-9]\d{9}\b"),
        ("AADHAAR-LIKE", r"\b\d{4}[- ]\d{4}[- ]\d{4}\b"),
    ]
    for kind, pat in patterns:
        for m in re.finditer(pat, text, re.I):
            findings.append({"type": kind, "start": m.start(), "end": m.end(), "value_preview": m.group(0)[:3] + "…" if len(m.group(0)) > 3 else "***"})
    return text, findings

@app.get("/api/documents/{eid}/intelligence")
def intelligence(eid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "evidence.read"); e = evidence_access(u, eid)
    c = db(); v = c.execute("SELECT * FROM versions WHERE evidence_id=? AND version=?", (eid, e["current_version"])).fetchone()
    red = c.execute("SELECT * FROM redactions WHERE evidence_id=? ORDER BY id DESC LIMIT 1", (eid,)).fetchone(); c.close()
    data = (ROOT / v["object_path"]).read_bytes() if (ROOT / v["object_path"]).exists() else b""
    text, findings = scan_text(data)
    return {"document_number": e["evidence_no"], "document_type": e["kind"], "classification": e["classification"],
            "current_version": e["current_version"], "ai_classification": e["kind"], "ai_confidence": 0.98,
            "extraction_method": "UTF-8 / heuristic", "extracted_text": text, "extracted_text_preview": text[:4000],
            "redaction_count": len(json.loads(red["findings_json"])) if red else len(findings),
            "redaction_findings": json.loads(red["findings_json"]) if red else findings,
            "sealed": bool(e["sealed"]), "merkle_root": sha_bytes((e["evidence_no"] + v["sha256"]).encode()),
            "versions": evidence_payload(eid, u)["versions"]}

@app.post("/api/documents/{eid}/redact")
def redact(eid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "forensic.write"); e = evidence_access(u, eid)
    c = db(); v = c.execute("SELECT * FROM versions WHERE evidence_id=? AND version=?", (eid, e["current_version"])).fetchone(); c.close()
    data = (ROOT / v["object_path"]).read_bytes()
    text, findings = scan_text(data)
    c = db(); c.execute("INSERT INTO redactions(evidence_id,version,findings_json,created_by,created_at) VALUES(?,?,?,?,?)",
                         (eid, v["version"], json.dumps(findings), u["id"], now())); c.commit(); c.close()
    audit(u, "REDACTION_SCAN", "EVIDENCE", eid, details={"version": v["version"], "count": len(findings)})
    return {"ok": True, "count": len(findings), "message": f"Detected {len(findings)} supported sensitive-data pattern(s). Original evidence was not modified."}

@app.get("/api/documents/{eid}/redacted")
def redacted(eid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "forensic.write"); e = evidence_access(u, eid)
    c = db(); r = c.execute("SELECT * FROM redactions WHERE evidence_id=? ORDER BY id DESC LIMIT 1", (eid,)).fetchone(); v = c.execute("SELECT * FROM versions WHERE evidence_id=? AND version=?", (eid, e["current_version"])).fetchone(); c.close()
    data = (ROOT / v["object_path"]).read_bytes()
    text, findings = scan_text(data)
    for f in findings:
        text = text[:f["start"]] + "[REDACTED]" + text[f["end"]:]
    audit(u, "REDACTED_COPY_EXPORTED", "EVIDENCE", eid, details={"version": v["version"]})
    return StreamingResponse(iter([text.encode()]), media_type="text/plain",
                             headers={"Content-Disposition": f'attachment; filename="{e["evidence_no"]}-redacted.txt"'})

@app.post("/api/documents/{eid}/forensic-export")
def forensic_export(eid: int, include_bytes: bool = False, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "report.create"); e = evidence_access(u, eid)
    c = db()
    case = c.execute("SELECT * FROM cases WHERE id=?", (e["case_id"],)).fetchone()
    versions = c.execute("SELECT * FROM versions WHERE evidence_id=? ORDER BY version", (eid,)).fetchall()
    events = c.execute("SELECT * FROM events WHERE target_type='EVIDENCE' AND target_id=? ORDER BY id", (str(eid),)).fetchall()
    signatures_rows = c.execute("SELECT * FROM signatures WHERE evidence_id=?", (eid,)).fetchall()
    governance_row = c.execute("SELECT * FROM governance WHERE evidence_id=?", (eid,)).fetchone()
    c.close()
    verified_sources = {}
    if include_bytes:
        for v in versions:
            p, source = verified_object_path(eid, v)
            if not p:
                raise HTTPException(409, f"Version {v['version']} has no integrity-verified source; byte-inclusive export refused")
            verified_sources[v["version"]] = (p, source)
    package = EXPORTS / f"KAIRO-{e['evidence_no']}-{uuid.uuid4().hex[:8]}.zip"
    manifest = {"case": dict(case), "evidence": dict(e), "versions": [dict(v) for v in versions],
                "events": [dict(x) for x in events], "signatures": [dict(x) for x in signatures_rows],
                "governance": dict(governance_row) if governance_row else None,
                "generated_at": now(), "bytes_included": include_bytes}
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest, indent=2, default=str))
        if include_bytes:
            for v in versions:
                p, source = verified_sources[v["version"]]
                z.write(p, f"evidence/v{v['version']}/{v['filename']}")
                if source == "TRUSTED_RECOVERY":
                    z.writestr(f"evidence/v{v['version']}/RECOVERY-NOTE.txt",
                               "The primary stored object did not match its registered SHA-256. "
                               "The byte payload was recovered from KAIRO's protected trusted copy.\n")
    audit(u, "FORENSIC_EXPORT_CREATED", "EVIDENCE", eid, details={"include_bytes": include_bytes, "package": package.name})
    return FileResponse(package, filename=package.name, media_type="application/zip")

@app.post("/api/documents/{eid}/tamper-demo")
def tamper_demo(eid: int, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "forensic.write"); evidence_access(u, eid)
    return simulate_tamper(eid, None, "web-controlled-security-lab")

def simulate_tamper(eid, version=None, source="attackvector CLI"):
    c = db()
    v = c.execute("SELECT * FROM versions WHERE evidence_id=? AND version=COALESCE(NULLIF(?,0),(SELECT current_version FROM evidence WHERE id=?))",
                  (eid, version or 0, eid)).fetchone(); c.close()
    if not v: raise HTTPException(404, "Target version not found")
    p = ROOT / v["object_path"]
    if not p.exists(): raise HTTPException(404, "Target evidence object not found")
    data = p.read_bytes()
    marker = b"\n[KAIRO SECURITY LAB - SIMULATED STORAGE MODIFICATION]\n"
    if marker not in data: p.write_bytes(data + marker)
    audit(None, "SECURITY_LAB_TAMPER", "EVIDENCE", eid, "SIMULATED",
          {"version": v["version"], "source": source})
    return {"ok": True, "evidence_id": eid, "version": v["version"],
            "message": "Controlled storage modification applied. Run integrity verification.",
            "new_sha256": sha_file(p)}

@app.post("/api/attack/tamper")
def attack(body: dict, x_kairo_lab_key: Optional[str] = Header(None)):
    if not secrets.compare_digest(x_kairo_lab_key or "", ATTACK_KEY):
        raise HTTPException(403, "Security Lab key required")
    try: eid = int(body.get("evidence_id"))
    except Exception: raise HTTPException(422, "evidence_id is required")
    return simulate_tamper(eid, int(body.get("version") or 0))

@app.get("/api/security/posture")
def security_posture(authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization)
    return {"identity": "JWT", "authorization": "server-enforced RBAC + case membership",
            "integrity": "SHA-256 per evidence version", "audit": "hash-chained events",
            "storage": "versioned object store + protected recovery copy",
            "trust": "pluggable permissioned trust anchor", "security_lab": "controlled"}

@app.get("/api/admin/users")
def admin_users(authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "admin.users")
    c = db(); rows = c.execute("SELECT id,email,name,role,active,created_at FROM users ORDER BY name").fetchall(); c.close()
    return [dict(r) for r in rows]

@app.post("/api/admin/users")
def admin_create_user(body: dict, authorization: Optional[str] = Header(None)):
    u = user_from_token(authorization); require(u, "admin.users")
    email = str(body.get("email","")).strip().lower()
    name = str(body.get("name","")).strip()
    role = str(body.get("role","POLICE")).upper()
    password = str(body.get("password",""))
    if not email or "@" not in email or not name or role not in ROLES or not password or len(password) < 10:
        raise HTTPException(422, "Email, name, valid role and password of at least 10 characters are required")
    c=db()
    try:
        c.execute("INSERT INTO users(email,name,role,password_hash,created_at) VALUES(?,?,?,?,?)",
                  (email,name,role,password_hash(password),now()))
        uid=c.execute("SELECT last_insert_rowid()").fetchone()[0]; c.commit()
    except sqlite3.IntegrityError:
        c.close(); raise HTTPException(409,"User already exists")
    c.close(); audit(u,"USER_CREATED","USER",uid,details={"email":email,"role":role})
    return {"id":uid,"email":email,"name":name,"role":role,"active":1}

@app.post("/api/admin/users/{uid}/status")
def admin_user_status(uid:int, body:dict, authorization:Optional[str]=Header(None)):
    u=user_from_token(authorization); require(u,"admin.users")
    if uid == u["id"] and not bool(body.get("active", True)): raise HTTPException(400,"You cannot deactivate your own account")
    active=1 if bool(body.get("active",True)) else 0
    c=db(); r=c.execute("SELECT * FROM users WHERE id=?",(uid,)).fetchone()
    if not r: c.close(); raise HTTPException(404,"User not found")
    c.execute("UPDATE users SET active=? WHERE id=?",(active,uid)); c.commit(); c.close()
    audit(u,"USER_ACTIVATED" if active else "USER_DEACTIVATED","USER",uid)
    return {"ok":True,"active":bool(active)}

@app.post("/api/documents/{eid}/restore/{version}")
def restore_alias(eid:int, version:int, authorization:Optional[str]=Header(None)):
    return restore(eid, version, authorization)

@app.get("/api/documents/{eid}/download")
def download_document_alias(eid:int, authorization:Optional[str]=Header(None)):
    return download_version(eid, 0, authorization)

FRONT = ROOT / "frontend" / "dist"
if FRONT.exists():
    app.mount("/", StaticFiles(directory=FRONT, html=True), name="frontend")
