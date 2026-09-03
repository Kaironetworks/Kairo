# KAIRO Release Acceptance

This package is the consolidated SIH26190 release candidate. It is deliberately conservative about claims.

## Verified in the package build

- Python backend source parses successfully.
- Fabric Gateway JavaScript parses successfully.
- Case membership authorization exists at the API boundary.
- Lead-investigator-only case membership changes are enforced.
- Evidence versions are immutable and version allocation is serialized per document.
- Document numbers use a database sequence.
- Evidence retrieval/export performs SHA-256 verification first.
- Integrity mismatch is represented as an incident.
- Sharing is limited to existing members of the same case.
- `VIEW` shares cannot retrieve evidence bytes; `DOWNLOAD` shares can.
- Session logout revokes the JWT JTI.
- The frontend has a render-error safety boundary so a component failure produces a controlled recovery screen instead of a blank page.
- Demo/tamper tooling uses the same S3-compatible storage protocol as the application and does not require an undeclared `minio` Python package.

## Runtime gates

These must be executed on the target Windows/WSL environment because this build environment does not contain the user's Docker services or frontend dependency tree:

1. `BUILD_KAIRO.ps1` — install locked frontend dependencies and build the bundle.
2. `START_KAIRO.ps1` — start PostgreSQL, MinIO, API and frontend.
3. `final_tools/final_stack_check.ps1` — verify local services.
4. Log in with a synthetic demo identity.
5. Exercise the evidence lifecycle.
6. Run the controlled tamper demonstration and verify the incident.
7. Run `fabric/scripts/bootstrap.sh` in WSL and start `blockchain-gateway`.
8. Anchor a verified document and record the **actual Fabric transaction ID** returned by the network.

No source-only Fabric claim is treated as a live blockchain proof.

## Production deployment boundary

This SIH release is a hardened working prototype, not a claim that a government production environment can be deployed without operational infrastructure. Production requires TLS/reverse proxy, centralized identity, KMS/HSM, HA database/object storage, distributed rate limiting, centralized logging/monitoring, backup/restore controls, network segmentation and jurisdiction-appropriate signature/compliance infrastructure.
