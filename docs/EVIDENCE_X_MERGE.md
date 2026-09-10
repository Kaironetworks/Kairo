# EvidenceX capability merge — KAIRO

KAIRO remains the security boundary. The EvidenceX-style capabilities are implemented as an intelligence/controls layer on top of KAIRO's existing JWT, RBAC, case membership, PostgreSQL, MinIO, immutable versions, audit chain, incidents, governance and Fabric integration.

## Added
- PDF/DOCX/TXT extraction with optional image OCR.
- Assisted document classification with confidence and matched signals.
- Extracted-text search through the existing case-scoped search endpoint.
- PII detection/redaction into a separate MinIO object; original evidence is never rewritten by redaction.
- Merkle root over all registered versions for the selected document.
- Evidence sealing with server-side modification blocking.
- Controlled tamper demonstration that changes stored bytes without changing the registered SHA-256, allowing the existing verification/incident workflow to detect it.
- Historical restore as a **new immutable version**, preserving the prior version rather than rewinding history.
- Retention-aware document deletion for administrators.
- Legal Officer and Administrator roles in addition to Investigator, Forensic Officer and Auditor.
- Intelligence Console in the React UI.

## Deliberate differences
- EvidenceX's `X-User` demo-header authentication was not copied; KAIRO's JWT session and server-side RBAC remain authoritative.
- EvidenceX's role-list document access was not used as a replacement for KAIRO case membership.
- Redaction never edits or replaces original evidence bytes.
- Restore creates a new version instead of changing the meaning of historical custody.
- MFA/TOTP from EvidenceX is not used as a second authentication mechanism by default because KAIRO already has authenticated, revocable sessions; adding a second factor should be configured as a deployment policy rather than a demo-only shared secret.
- OCR is optional. PDF text extraction uses `pypdf`; image OCR uses Pillow + the installed Tesseract engine. The app remains runnable when those optional capabilities are unavailable.

## Verification
Run the backend compile/unit checks and the frontend build on the target machine after dependency installation. This archive does not contain `node_modules`; the target machine should run `npm ci` in `frontend` before `npm run build`.
