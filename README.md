# KAIRO — Trust, engineered.

Secure digital evidence and document management for legal and investigative workflows — SIH 26190.

## Architecture

```text
KAIRO Web
   │
   ▼
FastAPI
   ├── PostgreSQL → identity, cases, metadata, RBAC, audit, custody, incidents
   └── MinIO/S3  → evidence bytes + trusted recovery copies
                         │
                         ▼
                    SHA-256 integrity
                         │
                ┌────────┴────────┐
                │                 │
           local trust chain   Fabric boundary
                │
                └── AttackVector (controlled lab only)
```

PostgreSQL is the system-of-record database. **It is not object storage.** Evidence bytes belong in S3-compatible object storage. MinIO is the reference S3 deployment. For a zero-install run, KAIRO automatically falls back to SQLite + versioned local storage; this fallback is for portable prototyping, not the production architecture.

## Department access

| Department | Main capabilities |
|---|---|
| Police / Law Enforcement | Cases, evidence registration/retrieval, verification, controlled sharing |
| Investigative / Specialized Agency | Investigation workflow, evidence lifecycle, collaboration, verification, assistive intelligence |
| Forensic / Scientific Laboratory | Integrity verification, versions, custody, restoration, signatures, intelligence, forensic export, trust |
| Judiciary / Legal Institution | Authorized case/evidence review, verification, custody, reports, legal hold |
| Audit / Compliance | Audit trail, incidents, trust ledger, governance oversight |
| System Administration | Users, roles and platform administration; does not silently rewrite evidence |

The API is the security boundary. UI visibility is never treated as authorization.

## Evidence lifecycle

1. Register evidence and calculate SHA-256 over the actual bytes.
2. Store an immutable version with a separate trusted recovery copy.
3. Legitimate updates create a new version; old versions remain intact.
4. Every important action creates an authenticated, hash-chained custody/audit event.
5. Verification recalculates the current stored bytes.
6. A mismatch creates an integrity incident.
7. An authorized forensic user can restore a trusted version as a **new version**; the incident remains in history.
8. Selected critical proofs can be anchored by the trust provider. Sensitive document bytes stay off-chain.

## Controlled attack demonstration

`attackvector/` contains the only intentionally adversarial component. It changes a demonstration evidence object through a protected lab endpoint. It does not exploit the host operating system.

Example:

```text
ATTACKVECTOR.bat http://HOST-IP:8000 1 1
```

Then KAIRO verification should show:

```text
REGISTERED SHA-256 != OBSERVED SHA-256
        ↓
INTEGRITY MISMATCH
        ↓
INCIDENT
        ↓
RESTORE TRUSTED VERSION
        ↓
NEW RESTORATION VERSION
        ↓
VERIFIED
```

## Run on a clean Windows laptop

Requires Python 3.11+.

```text
INSTALL_KAIRO.bat
START_KAIRO.bat
```

The shipped frontend is prebuilt, so **Node/npm and Docker are not required to run the included prototype**.

The host prints a LAN address. Every other laptop on the same Wi-Fi opens that address and uses the **same backend, database and evidence store**.

## Demo accounts

All seeded accounts use the same prototype password:

```text
KairoDemo!2026
```

```text
police@kairo.local
investigator@kairo.local
forensic@kairo.local
legal@kairo.local
auditor@kairo.local
admin@kairo.local
```

For zero-install SQLite mode, the seeded demo identities are deterministically repaired on startup. Set `KAIRO_RESET_DEMO_PASSWORDS=0` when using a persistent deployment where demo identities must not be overwritten.

## Production-style PostgreSQL + MinIO

Set:

```text
KAIRO_SECRET=use-a-random-secret-of-at-least-32-characters
KAIRO_DATABASE_URL=postgresql+psycopg://kairo:PASSWORD@HOST:5432/kairo
KAIRO_S3_ENDPOINT=http://HOST:9000
KAIRO_S3_ACCESS_KEY=ACCESS_KEY
KAIRO_S3_SECRET_KEY=SECRET_KEY
KAIRO_S3_EVIDENCE_BUCKET=kairo-evidence
KAIRO_S3_TRUSTED_BUCKET=kairo-trusted
```

KAIRO creates the required buckets and enables S3 object versioning where supported.

## Trust / blockchain

The portable prototype has a **real hash-chained local trust ledger** and a clearly separated trust-anchor provider. It does not claim that Fabric is connected when it is not.

`blockchain/` is the boundary for a permissioned Hyperledger Fabric deployment. The intended production model stores cryptographic proof metadata on the ledger, not FIR/PDF/video bytes.

## Repository structure

```text
frontend/       UI source + shipped build
backend/        FastAPI application
blockchain/     trust-anchor provider + CLI
attackvector/   controlled storage-tamper lab
 data/          synthetic demo documents and runtime storage
README.md
LICENSE
```
