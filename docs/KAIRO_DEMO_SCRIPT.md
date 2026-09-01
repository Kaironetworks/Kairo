# KAIRO — Final Jury Demo Script
1. Authenticate as an investigator.
2. Open the active investigation and evidence record.
3. Show current version, SHA-256 fingerprint and classification.
4. Create one legitimate version; show actor, authorization and timestamp.
5. Verify integrity: PASS.
6. Run the controlled storage-tamper demonstration.
7. Verify again: SHA mismatch; incident opens.
8. Explain that a hash detects modification but does not identify the physical attacker.
9. Show chain of custody, audit trail and trust ledger.
10. Search and retrieve an exact version; release occurs only after integrity verification.
11. Share to an authorized account with expiry/revocation and demonstrate recipient retrieval.
12. Create and verify a digital signature over the evidence fingerprint.
13. Show retention/legal hold and forensic export.
14. If Fabric Gateway is available, anchor the current proof and show the returned Fabric transaction ID.

## Architecture statement
Sensitive evidence bytes remain off-chain in protected object storage. PostgreSQL stores operational metadata. SHA-256 provides content integrity. The cryptographic trust ledger links audit events. Hyperledger Fabric anchors proof/custody metadata; it does not store the sensitive file itself.

## Honest claims
- SHA-256 detects content change; it does not identify an attacker.
- The prototype signing service is not claimed to be a jurisdiction-qualified e-signature service.
- Fabric is an additional trust anchor; the core KAIRO lifecycle does not depend on blockchain availability.
