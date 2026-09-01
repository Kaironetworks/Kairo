# KAIRO Update 8 — Search & Secure Retrieval

Substantial update to the SIH26190-aligned evidence lifecycle.

## What changed
- Protected search and retrieval workspace.
- Metadata search across case/document fields and latest filename.
- Case/type/classification filters.
- Exact immutable-version retrieval.
- Integrity verification before evidence bytes are released.
- Retrieval success/block events are audited and anchored by the existing KAIRO trust layer.

## Existing layers preserved
- JWT authentication
- RBAC / least privilege
- PostgreSQL metadata
- MinIO evidence storage
- SHA-256 integrity
- Immutable versioning
- Chain of custody
- Cryptographic trust ledger
- Incident response
- Hyperledger Fabric integration path (network activation remains a separate deployment/test step)

## Apply
Extract this update over the existing `C:\Developer\Kairo` project. Do not delete PostgreSQL or MinIO volumes.
