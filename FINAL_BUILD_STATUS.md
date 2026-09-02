# KAIRO Final Build Status

This package is the consolidated final prototype build.

## Locked product direction
- Light-only government operations interface.
- Indian public-sector simplicity: clear hierarchy, restrained colour, accessible controls.
- KAIRO-specific evidence integrity and forensic workflows.
- No dark mode, neon, marketing/pricing surfaces, or decorative AI-style UI.

## Core capabilities retained
Authentication, RBAC, cases, evidence ingestion, versioning, SHA-256 verification,
chain of custody, audit trail, trust ledger, incidents, controlled sharing,
cryptographic signatures, governance/legal hold, forensic export and Fabric trust-anchor path.

## Important implementation behaviour
- Search defaults to all cases/types/classifications.
- API validation errors are surfaced with field-level detail when available.
- Binary downloads and forensic exports use timeout-aware requests.
- Logout is permanently visible at the bottom of the navigation.
- Fabric availability is shown honestly and does not define core control-plane health.
- Evidence download and byte-inclusive forensic export verify registered SHA-256 before releasing bytes.

## Verification performed in this environment
- Backend Python modules compile successfully.
- API JavaScript syntax was checked previously and the final API changes are syntactically structured.
- Source/package structure and ZIP contents were checked.
- A full browser production build could not be completed here because npm dependency installation timed out in the execution environment. Therefore this package is not falsely labelled as browser-runtime-verified.

## Demo principle
The final jury flow should be:
CASE -> EVIDENCE -> VERSION -> SHA-256 -> VERIFY -> CUSTODY -> AUDIT -> TRUST -> TAMPER -> INCIDENT -> FORENSIC EXPORT -> FABRIC ANCHOR.

Do not claim a Fabric transaction is real until the live environment returns a valid transaction ID.
