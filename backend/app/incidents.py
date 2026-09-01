import json
from sqlalchemy import text
from sqlalchemy.orm import Session

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS security_incidents (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL,
    version INTEGER,
    incident_type VARCHAR(80) NOT NULL,
    severity VARCHAR(30) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
    detected_by BIGINT,
    expected_sha256 VARCHAR(64),
    observed_sha256 VARCHAR(64),
    authorized_event_id BIGINT,
    explanation TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolved_by BIGINT,
    resolution TEXT
);
CREATE INDEX IF NOT EXISTS ix_security_incidents_document ON security_incidents(document_id);
CREATE INDEX IF NOT EXISTS ix_security_incidents_status ON security_incidents(status);
"""

def ensure_incidents(db: Session):
    for statement in [x.strip() for x in CREATE_SQL.split(';') if x.strip()]:
        db.execute(text(statement))
    db.commit()

def open_integrity_incident(db: Session, document_id: int, version: int, detected_by: int | None,
                            expected: str | None, observed: str | None, authorized_event_id: int | None):
    existing = db.execute(text("""
        SELECT id FROM security_incidents
        WHERE document_id=:document_id AND version=:version AND incident_type='UNAUTHORIZED_MODIFICATION' AND status='OPEN'
        ORDER BY id DESC LIMIT 1
    """), {"document_id": document_id, "version": version}).first()
    if existing:
        return existing[0], False
    explanation = (
        "Evidence bytes differ from the registered fingerprint. No successful authorized version-creation "
        "event explains the observed change. The detector identifies an unauthorized modification condition; "
        "it does not claim to identify the physical attacker."
    )
    row = db.execute(text("""
        INSERT INTO security_incidents
        (document_id, version, incident_type, severity, status, detected_by,
         expected_sha256, observed_sha256, authorized_event_id, explanation)
        VALUES (:document_id,:version,'UNAUTHORIZED_MODIFICATION','CRITICAL','OPEN',:detected_by,
                :expected,:observed,:authorized_event_id,:explanation)
        RETURNING id
    """), locals()).first()
    db.commit()
    return row[0], True

def list_incidents(db: Session, status: str | None = None):
    q = """
      SELECT id, document_id, version, incident_type, severity, status, detected_by,
             expected_sha256, observed_sha256, authorized_event_id, explanation,
             created_at, resolved_at, resolved_by, resolution
      FROM security_incidents
    """
    params = {}
    if status:
        q += " WHERE status=:status"
        params["status"] = status
    q += " ORDER BY CASE WHEN status='OPEN' THEN 0 ELSE 1 END, created_at DESC"
    return [dict(r) for r in db.execute(text(q), params).mappings().all()]

def resolve_incident(db: Session, incident_id: int, user_id: int, resolution: str):
    row = db.execute(text("""
      UPDATE security_incidents
      SET status='RESOLVED', resolved_at=NOW(), resolved_by=:user_id, resolution=:resolution
      WHERE id=:id AND status='OPEN'
      RETURNING id
    """), {"id": incident_id, "user_id": user_id, "resolution": resolution}).first()
    if not row:
        return False
    db.commit()
    return True
