# KAIRO — Final Core Integration

This overlay is for the latest KAIRO Updates 12–14 tree. It closes the remaining integration gap without changing the existing application architecture.

## Core completed
- JWT authentication and RBAC / least privilege
- Case-centric legal/investigation document management
- MinIO evidence-object storage + PostgreSQL metadata
- Immutable document versions and SHA-256 evidence fingerprints
- Integrity verification before release / anchoring / forensic export
- Chain of custody
- Chained local trust ledger for auditable event integrity
- Security incident creation/resolution on integrity mismatch
- Search, filtering, exact-version retrieval
- Account-bound sharing with expiry/revocation
- RSA-PSS/SHA-256 evidence-fingerprint signatures (prototype)
- Retention policy and legal hold governance
- Forensic evidence package export
- Security headers, request IDs, upload ceiling, login throttling, duplicate-signature prevention
- Hyperledger Fabric `kairo-trust` chaincode + Org1/Org2 permissioned network path

## Final integration correction
The Fabric network created by the test-network lives in the WSL Linux filesystem. The final `start_gateway.sh` auto-detects:

`$HOME/kairo-fabric/fabric-samples`

before checking optional alternate locations. It therefore does not require copying Fabric identities into the Windows project tree.

## One-command gateway start
From WSL:

```bash
cd /mnt/c/Developer/Kairo/fabric/scripts
./start_gateway.sh
```

Keep that terminal open.

## API configuration
The Windows FastAPI process should use:

`KAIRO_BLOCKCHAIN_URL=http://127.0.0.1:8090`

## Real blockchain proof
A blockchain integration claim is considered verified only after KAIRO's document anchor action returns a Fabric record containing a real `txId`. The local trust ledger is separate and must not be described as distributed blockchain.

## Architecture
Frontend → FastAPI → RBAC → PostgreSQL/MinIO → SHA-256 → custody → audit → local trust ledger → Fabric Gateway → permissioned Fabric.

Sensitive document bytes remain off-chain. Fabric stores cryptographic proof/custody metadata.
