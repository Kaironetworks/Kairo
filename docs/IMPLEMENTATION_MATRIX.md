# KAIRO Implementation Matrix

| Capability | Implementation state |
|---|---|
| Authentication | JWT session authentication |
| Authorization | Server-side RBAC / permission checks |
| Case registry | Read + create workflow |
| Evidence ingestion | Protected upload workflow |
| Object storage | S3-compatible / MinIO |
| Versioning | Non-destructive version records |
| Integrity | SHA-256 recalculation and comparison |
| Custody | Lifecycle/custody records |
| Audit | Protected audit event trail |
| Trust ledger | Local cryptographic hash chain |
| Blockchain | Hyperledger Fabric Gateway integration |
| Fabric chaincode | JavaScript |
| Sharing | Account-bound, expiring, revocable |
| Signatures | RSA-PSS cryptographic signature prototype |
| Governance | Retention + legal hold state |
| Incidents | Integrity incident workflow |
| Forensic export | Metadata + optional verified bytes |
| AI analysis | Not implemented |
| Keycloak/OIDC | Not implemented in current application |
| Go chaincode | Not implemented; current chaincode is JavaScript |
| Qualified legal e-signature | Not claimed; current signature is a cryptographic prototype |
| HSM/KMS production key management | Deployment-dependent / not implemented |
| Automated retention disposal | Governance state exists; automated disposal is not implemented |
