import hashlib
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import AuditEvent, Document, DocumentVersion, User
from .storage import get_bytes


def _parse_details(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _actor(db: Session, actor_id: int | None):
    if actor_id is None:
        return None
    user = db.get(User, actor_id)
    if not user:
        return {"id": actor_id, "email": "unknown", "full_name": "Unknown actor", "role": "UNKNOWN"}
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
    }


def build_custody_record(db: Session, document_id: int, verify_bytes: bool = True):
    doc = db.get(Document, document_id)
    if not doc:
        return None

    version = db.scalar(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version.desc())
    )
    if not version:
        return {
            "document_id": document_id,
            "document_number": doc.document_number,
            "status": "NO_VERSION",
            "explanation": "The document has no registered evidence version.",
            "current_version": None,
            "expected_sha256": None,
            "observed_sha256": None,
            "hash_match": None,
            "authorized_change": None,
            "events": [],
        }

    events = list(
        db.scalars(
            select(AuditEvent)
            .where(
                AuditEvent.target_type == "DOCUMENT",
                AuditEvent.target_id == str(document_id),
            )
            .order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc())
        )
    )

    version_events = []
    for event in events:
        details = _parse_details(event.details)
        if event.action in {"DOCUMENT_UPLOAD", "DOCUMENT_VERSION_CREATE"}:
            event_version = details.get("version")
            if event.action == "DOCUMENT_UPLOAD" and event_version is None:
                event_version = 1
            if event_version == version.version and event.result == "SUCCESS":
                version_events.append(event)

    authorized_event = version_events[-1] if version_events else None
    authorized_actor = _actor(db, authorized_event.actor_id if authorized_event else version.uploaded_by)

    observed = None
    hash_match = None
    storage_error = None
    if verify_bytes:
        try:
            observed = hashlib.sha256(get_bytes(version.object_key)).hexdigest()
            hash_match = observed == version.sha256
        except Exception as exc:
            storage_error = str(exc)

    if storage_error:
        status = "STORAGE_UNAVAILABLE"
        explanation = "KAIRO could not read the registered evidence object, so custody cannot be verified."
    elif hash_match is False:
        status = "INTEGRITY_INCIDENT"
        explanation = (
            "The current evidence bytes do not match the fingerprint registered for this version. "
            "No new authorized version event explains the change. KAIRO therefore treats it as an unauthorized modification incident."
        )
    elif authorized_event is None:
        status = "CUSTODY_GAP"
        explanation = (
            "The current version exists, but KAIRO cannot find the successful authorized creation event "
            "that should explain how this version entered the evidence lifecycle."
        )
    else:
        status = "CONTROLLED"
        explanation = (
            "The current evidence bytes match the registered fingerprint, and the current version is "
            "linked to a successful authorized KAIRO action by the recorded account."
        )

    custody_events = []
    for event in events:
        details = _parse_details(event.details)
        event_version = details.get("version")
        if event.action in {"DOCUMENT_UPLOAD", "DOCUMENT_VERSION_CREATE"} and event_version is None:
            event_version = 1 if event.action == "DOCUMENT_UPLOAD" else None
        custody_events.append({
            "id": event.id,
            "action": event.action,
            "result": event.result,
            "version": event_version,
            "actor": _actor(db, event.actor_id),
            "timestamp": event.created_at,
            "details": details,
        })

    return {
        "document_id": document_id,
        "document_number": doc.document_number,
        "status": status,
        "explanation": explanation,
        "current_version": {
            "version": version.version,
            "sha256": version.sha256,
            "expected_sha256": version.sha256,
            "observed_sha256": observed,
            "verified": hash_match is True,
        },
        "expected_sha256": version.sha256,
        "observed_sha256": observed,
        "hash_match": hash_match,
        "authorized_change": {
            "event_id": authorized_event.id if authorized_event else None,
            "action": authorized_event.action if authorized_event else None,
            "version": version.version,
            "actor": authorized_actor,
            "timestamp": authorized_event.created_at if authorized_event else version.created_at,
            "permission": "document:version:create" if authorized_event else None,
        },
        "events": custody_events,
    }
