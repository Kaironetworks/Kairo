import hashlib
import json
import secrets
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS trust_blocks (
    block_index BIGSERIAL PRIMARY KEY,
    audit_event_id BIGINT UNIQUE NOT NULL,
    previous_hash VARCHAR(64) NOT NULL,
    event_hash VARCHAR(64) NOT NULL,
    transaction_id VARCHAR(64) UNIQUE NOT NULL,
    action VARCHAR(120) NOT NULL,
    target_type VARCHAR(80) NOT NULL,
    target_id VARCHAR(120) NOT NULL,
    result VARCHAR(40) NOT NULL,
    payload TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_trust_blocks_target ON trust_blocks(target_type, target_id);
"""


def ensure_ledger(db: Session):
    # PostgreSQL accepts multiple statements in one execute with this driver.
    for statement in [x.strip() for x in CREATE_SQL.split(';') if x.strip()]:
        db.execute(text(statement))
    db.commit()
    backfill_audit_events(db)


def _canonical(action, target_type, target_id, result, details, previous_hash, audit_event_id):
    payload = {
        "audit_event_id": audit_event_id,
        "action": action,
        "target_type": target_type,
        "target_id": str(target_id),
        "result": result,
        "details": details or "",
        "previous_hash": previous_hash,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _last_hash(db: Session) -> str:
    row = db.execute(
        text("SELECT event_hash FROM trust_blocks ORDER BY block_index DESC LIMIT 1")
    ).first()
    return row[0] if row else "0" * 64


def anchor_audit_event(db: Session, audit_event):
    existing = db.execute(
        text("SELECT block_index, transaction_id, event_hash FROM trust_blocks WHERE audit_event_id=:id"),
        {"id": audit_event.id},
    ).first()
    if existing:
        return {"block_index": existing[0], "transaction_id": existing[1], "event_hash": existing[2]}

    previous_hash = _last_hash(db)
    canonical = _canonical(
        audit_event.action,
        audit_event.target_type,
        audit_event.target_id,
        audit_event.result,
        audit_event.details,
        previous_hash,
        audit_event.id,
    )
    event_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    transaction_id = hashlib.sha256(
        f"KAIRO-TX:{audit_event.id}:{event_hash}:{secrets.token_hex(8)}".encode("utf-8")
    ).hexdigest()

    row = db.execute(
        text("""
            INSERT INTO trust_blocks
            (audit_event_id, previous_hash, event_hash, transaction_id, action,
             target_type, target_id, result, payload)
            VALUES (:audit_event_id, :previous_hash, :event_hash, :transaction_id,
                    :action, :target_type, :target_id, :result, :payload)
            RETURNING block_index, transaction_id, event_hash
        """),
        {
            "audit_event_id": audit_event.id,
            "previous_hash": previous_hash,
            "event_hash": event_hash,
            "transaction_id": transaction_id,
            "action": audit_event.action,
            "target_type": audit_event.target_type,
            "target_id": str(audit_event.target_id),
            "result": audit_event.result,
            "payload": canonical,
        },
    ).first()
    db.commit()
    return {"block_index": row[0], "transaction_id": row[1], "event_hash": row[2]}


def backfill_audit_events(db: Session):
    from .models import AuditEvent

    events = list(db.scalars(__import__('sqlalchemy').select(AuditEvent).order_by(AuditEvent.id)))
    for event in events:
        anchor_audit_event(db, event)


def verify_ledger(db: Session):
    rows = db.execute(text("""
        SELECT block_index, audit_event_id, previous_hash, event_hash,
               transaction_id, action, target_type, target_id, result, payload
        FROM trust_blocks
        ORDER BY block_index ASC
    """)).all()

    expected_previous = "0" * 64
    failures = []
    for row in rows:
        canonical = json.loads(row[9])
        recomputed = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if row[2] != expected_previous:
            failures.append({"block_index": row[0], "reason": "PREVIOUS_HASH_MISMATCH"})
        if recomputed != row[3]:
            failures.append({"block_index": row[0], "reason": "EVENT_HASH_MISMATCH"})
        expected_previous = row[3]

    return {
        "verified": not failures,
        "blocks": len(rows),
        "latest_block": rows[-1][0] if rows else 0,
        "latest_hash": rows[-1][3] if rows else "0" * 64,
        "failures": failures,
    }


def list_blocks(db: Session, limit: int = 50):
    rows = db.execute(text("""
        SELECT block_index, audit_event_id, previous_hash, event_hash,
               transaction_id, action, target_type, target_id, result, created_at
        FROM trust_blocks
        ORDER BY block_index DESC
        LIMIT :limit
    """), {"limit": limit}).mappings().all()
    return [dict(row) for row in rows]


def document_anchors(db: Session, document_id: int, limit: int = 20):
    rows = db.execute(text("""
        SELECT block_index, audit_event_id, previous_hash, event_hash,
               transaction_id, action, target_type, target_id, result, created_at
        FROM trust_blocks
        WHERE target_type='DOCUMENT' AND target_id=:document_id
        ORDER BY block_index DESC
        LIMIT :limit
    """), {"document_id": str(document_id), "limit": limit}).mappings().all()
    return [dict(row) for row in rows]
