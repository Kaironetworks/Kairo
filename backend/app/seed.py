from sqlalchemy import select
from .db import Base, engine, SessionLocal
from .models import User, Case, Document, DocumentVersion
from .security import hash_password
from .storage import ensure_bucket, put_bytes
import hashlib

DEMO_PDF = b"%PDF-1.4\n% KAIRO fictional demonstration document\n%%EOF\n"

def run():
    Base.metadata.create_all(bind=engine)
    ensure_bucket()
    db = SessionLocal()
    try:
        for email, name, role in [
            ("investigator@kairo.local", "Arjun Kumar", "INVESTIGATING_OFFICER"),
            ("forensic@kairo.local", "Priya Nair", "FORENSIC_OFFICER"),
            ("auditor@kairo.local", "Ravi Menon", "AUDITOR"),
        ]:
            if not db.scalar(select(User).where(User.email == email)):
                db.add(User(email=email, full_name=name, role=role, password_hash=hash_password("KairoDemo!2026")))
        db.commit()

        case = db.scalar(select(Case).where(Case.case_number == "CASE-KR-2026-001"))
        if not case:
            case = Case(
                case_number="CASE-KR-2026-001",
                title="Digital Transaction Investigation",
                description="Fictional demonstration investigation used to demonstrate KAIRO's secure document lifecycle.",
                status="UNDER_INVESTIGATION",
                priority="HIGH",
                station="Cyber Crime Police Station, Chennai",
                is_demo=True,
            )
            db.add(case)
            db.commit()

        if not db.scalar(select(Document).where(Document.document_number == "KAIRO-DOC-00001")):
            investigator = db.scalar(select(User).where(User.email == "investigator@kairo.local"))
            doc = Document(
                document_number="KAIRO-DOC-00001",
                case_id=case.id,
                title="First Information Report",
                document_type="FIR",
                classification="RESTRICTED",
                current_version=1,
            )
            db.add(doc)
            db.flush()
            key = f"cases/{case.case_number}/documents/{doc.id}/v1/FIR-2026-001.pdf"
            put_bytes(key, DEMO_PDF, "application/pdf")
            db.add(DocumentVersion(
                document_id=doc.id,
                version=1,
                object_key=key,
                original_filename="FIR-2026-001.pdf",
                content_type="application/pdf",
                size_bytes=len(DEMO_PDF),
                sha256=hashlib.sha256(DEMO_PDF).hexdigest(),
                uploaded_by=investigator.id,
            ))
            db.commit()
        print("KAIRO seed complete.")
    finally:
        db.close()

if __name__ == "__main__":
    run()
