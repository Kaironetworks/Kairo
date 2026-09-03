# KAIRO Implementation Matrix

| Capability | Current implementation | State |
|---|---|---|
| Authentication | JWT with public local User ID aliases; revocable session JTI | COMPLETE |
| Authorization | Server-side RBAC plus case membership scope | COMPLETE |
| Case registry | Read/create plus case membership management | COMPLETE |
| Evidence ingestion | Protected multipart upload to MinIO with metadata in PostgreSQL | COMPLETE |
| Object storage | S3-compatible MinIO; server-generated versioned object paths | COMPLETE |
| Versioning | Immutable versions; PostgreSQL advisory lock serializes per-document version allocation | COMPLETE |
| Integrity | Actual byte SHA-256 recalculation before verification/retrieval/export | COMPLETE |
| Custody | Audit-derived lifecycle record with authorized actor/action linkage | COMPLETE |
| Audit | Protected audit event trail with denied-action records | COMPLETE |
| Trust ledger | Local SHA-256 chained audit ledger | COMPLETE |
| Blockchain | Hyperledger Fabric Gateway integration with real transaction ID returned by Fabric | INTEGRATION-READY / LIVE PROOF REQUIRES FABRIC RUNTIME |
| Fabric chaincode | JavaScript `kairo-trust` contract | COMPLETE FOR PROTOTYPE |
| Sharing | Account-bound, permission-specific, expiring and revocable | COMPLETE |
| Signatures | RSA-PSS over registered SHA-256 fingerprint | CRYPTOGRAPHIC PROTOTYPE |
| Governance | Retention + legal hold + conservative retention scan/disposition eligibility | COMPLETE FOR PROTOTYPE |
| Incidents | Integrity incident creation, scoped read, investigator-only resolution | COMPLETE |
| Search | Metadata search with case-scope enforcement | COMPLETE |
| Forensic export | Metadata package + optional byte-inclusive integrity-checked ZIP | COMPLETE |
| AI analysis | Not required by the SIH problem; intentionally not used as a dependency | OPTIONAL / NOT IMPLEMENTED |
| Keycloak/OIDC | Not required for the local prototype; current identity layer is JWT | NOT IMPLEMENTED |
| Qualified legal e-signature | Requires external qualified trust/service infrastructure | NOT IMPLEMENTED |
| KMS/HSM | Deployment integration required for production key custody | DEPLOYMENT-DEPENDENT |
| Distributed rate limiting | Current local limiter is single-process; production should use shared infrastructure | DEPLOYMENT-DEPENDENT |
| Automatic destruction | Expiry is evaluated and protected records are withheld; irreversible deletion requires explicit governance policy | CONSERVATIVE PROTOTYPE |

## Completion rule

A capability is not described as live merely because source code exists. Fabric is only “live” when the KAIRO anchor action returns a transaction ID from a running Fabric network. Production KMS/HSM, qualified signatures, OIDC deployment and HA infrastructure remain deployment-level concerns rather than pretending they are present locally.
