# KAIRO

### Secure evidence infrastructure for legal & investigation workflows

**Trust, engineered into every document.**

KAIRO is a secure digital document management and evidence-integrity platform for organizations handling sensitive legal and investigation records.

It treats a document as more than a file. Each protected record has an identity, access policy, version lineage, integrity proof, custody history and auditable lifecycle.

---

## What KAIRO solves

Legal and investigative teams work with FIRs, police reports, investigation records, witness statements, charge sheets, court filings, evidence records, forensic reports, legal notices and judgments.

The core problems are straightforward:

| Problem | KAIRO response |
|---|---|
| Documents scattered across systems | Case-centric centralized evidence workspace |
| Unauthorized access | Authenticated identity + RBAC + server-side authorization |
| Document tampering | SHA-256 fingerprint verification |
| Silent overwrites | Immutable, non-destructive version lineage |
| Poor accountability | Audit trail + chain of custody |
| Slow retrieval | Protected metadata search and retrieval |
| Uncontrolled collaboration | Account-bound, expiring and revocable sharing |
| Integrity disputes | Recalculation, comparison and incident workflow |
| Retention requirements | Retention and legal-hold controls |
| Need for independent trust | Permissioned Hyperledger Fabric anchoring |

The objective is not simply to store documents. It is to make their **identity, history, access and integrity verifiable**.

---

## The KAIRO model

```text
                         KAIRO
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
     IDENTITY           EVIDENCE            POLICY
     RBAC/JWT        Case + documents     Access rules
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
                    INTEGRITY ENGINE
                           │
                       SHA-256
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
       VERSION          CUSTODY           AUDIT
       lineage          history           events
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                      TRUST LAYER
                           │
             Cryptographic trust ledger
                           +
                  Hyperledger Fabric
                           │
                           ▼
                  VERIFIABLE RECORD
```

### Core architectural principle

> **Separate the document from its proof.**

Evidence bytes remain in protected object storage. Metadata, lifecycle records and cryptographic proofs remain in the application and trust layers. Selected critical proofs can be anchored to a permissioned blockchain.

---

## Evidence lifecycle

```text
REGISTER
   ↓
PROTECT
   ↓
FINGERPRINT
   ↓
VERSION
   ↓
VERIFY
   ↓
ACCESS / SHARE / SIGN
   ↓
AUDIT
   ↓
ANCHOR
   ↓
ARCHIVE / GOVERN
```

A document therefore becomes a controlled case record rather than an anonymous file.

---

## Integrity verification

KAIRO does not assume that stored bytes are trustworthy simply because they exist.

When verification is requested, KAIRO recalculates the SHA-256 fingerprint from the current evidence bytes and compares it with the registered fingerprint.

```text
Registered SHA-256
        │
        │ compare
        ▼
Current evidence bytes
        │
      SHA-256
        │
        ▼
Observed SHA-256
        │
   ┌────┴─────┐
   │          │
 MATCH     MISMATCH
   │          │
   ▼          ▼
VERIFIED   INCIDENT
```

A mismatch is treated as a security event, not merely a failed file operation.

---

## Version lineage

Existing evidence is never silently overwritten through the version workflow.

```text
Document
  ├── Version 01 → SHA-256 A
  ├── Version 02 → SHA-256 B
  ├── Version 03 → SHA-256 C
  └── Version 04 → SHA-256 D
```

This allows investigators and reviewers to reconstruct which version existed and when it entered the controlled workflow.

---

## Chain of custody

Important lifecycle operations become traceable events containing actor, action, timestamp and document/version context.

```text
Created
  ↓
Registered
  ↓
Verified
  ↓
Accessed
  ↓
Versioned
  ↓
Shared / Signed
  ↓
Anchored
  ↓
Archived
```

---

## Tamper response

KAIRO explicitly distinguishes an authorized change from a storage-level integrity failure.

```text
AUTHORIZED CHANGE
identity → permission → version event → new SHA-256

UNAUTHORIZED MODIFICATION
stored bytes → SHA-256 mismatch → incident → investigation
```

The system proves that the registered bytes and current bytes differ. A hash mismatch by itself does **not** identify an attacker.

---

## Trust architecture

```text
┌───────────────────────────────────────────────┐
│                    CLIENT                     │
│             React + Vite application          │
└───────────────────────┬───────────────────────┘
                        │
┌───────────────────────▼───────────────────────┐
│                APPLICATION                    │
│ FastAPI · auth · RBAC · lifecycle · policies │
└──────────────┬───────────────────┬────────────┘
               │                   │
               ▼                   ▼
       ┌───────────────┐   ┌──────────────────┐
       │  PostgreSQL   │   │ Object storage   │
       │ metadata/audit│   │ protected bytes  │
       └───────┬───────┘   └────────┬─────────┘
               │                    │
               └─────────┬──────────┘
                         ▼
                ┌────────────────┐
                │   TRUST LAYER   │
                │ hash chain      │
                │ custody proofs  │
                │ anchor records  │
                └────────┬────────┘
                         ▼
                ┌────────────────┐
                │ Hyperledger     │
                │ Fabric          │
                │ permissioned    │
                │ trust anchor    │
                └────────────────┘
```

Blockchain is therefore a **trust boundary**, not a replacement for the operational database or evidence store.

---

## Investigation workspace

KAIRO is organized around investigations and evidence collections.

```text
INVESTIGATION
│
├── Case identity
├── Classification / priority
├── Evidence collection
│   ├── Document
│   │   ├── Versions
│   │   ├── Integrity
│   │   ├── Custody
│   │   └── Trust anchor
│   └── Document
│
├── Security incidents
├── Controlled sharing
├── Digital signatures
└── Governance
```

This preserves investigation context throughout the document lifecycle.

---

## Security controls

- Authenticated sessions
- Role-based access control
- Server-side permission enforcement
- Protected object storage
- SHA-256 content fingerprints
- Immutable document versions
- Chain-of-custody records
- Auditable authorization failures
- Security response headers
- Upload size controls
- Login rate limiting
- Controlled sharing and revocation
- Cryptographic signing workflow
- Retention and legal-hold controls
- Integrity incident management
- Forensic export
- Cryptographic trust ledger
- Permissioned blockchain anchoring

---

## Roles

### Investigating Officer

Case work, evidence intake, retrieval, verification and controlled collaboration.

### Forensic Officer

Evidence integrity, version lineage, custody, verification, signatures and forensic export.

### Auditor

Authorized review of lifecycle activity, governance, authorization decisions and audit records.

Permissions are enforced at the API boundary; the interface is not the security boundary.

---

## Product principles

**Evidence first** — the trusted record is the primary object.

**Never silently overwrite** — historical versions remain identifiable.

**Verify before trust** — integrity is calculated from evidence bytes.

**Least privilege** — protected operations require explicit authorization.

**Documents stay off-chain** — the ledger is for proofs and selected lifecycle events.

**Failures stay visible** — unavailable infrastructure is never presented as successful trust.

**Auditability is native** — important actions produce traceable events.

---

## Technology

| Layer | Technology |
|---|---|
| Client | React, Vite |
| API | FastAPI, Python |
| Authentication | JWT-based authenticated sessions |
| Authorization | RBAC + server-side permission enforcement |
| Database | PostgreSQL |
| Evidence storage | S3-compatible object storage / MinIO development environment |
| Integrity | SHA-256 |
| Trust ledger | Cryptographic hash-chain ledger |
| Distributed trust | Hyperledger Fabric integration |
| Fabric gateway | Node.js + Fabric Gateway |
| UI | Responsive operations-console interface |
| Local orchestration | Docker Compose |

---

## Repository structure

```text
Kairo/
├── backend/              # API, security and evidence lifecycle
├── frontend/             # React application
├── blockchain-gateway/   # Fabric Gateway service
├── fabric/               # Fabric configuration, scripts and chaincode
├── security-lab/         # Security validation utilities
├── final_tools/          # Demo/release validation utilities
├── docs/                 # Architecture and operational documentation
├── docker-compose.yml    # Local service orchestration
└── README.md
```

The project does not depend on a developer-specific machine path.

---

## Project context

KAIRO is the solution developed by **Kairo Networks** for **SIH26190 — Secure Digital Document Management System for Legal and Investigation Documents** under the Blockchain & Cybersecurity theme.

The implementation is centered on the requirements of secure centralized storage, confidentiality, unauthorized-modification detection, version control, auditability, search and retrieval, authorized collaboration, governance and evidentiary integrity.

---

## Status

KAIRO is being developed as a complete working prototype with an implementation path toward production deployment. Deployment-specific identity infrastructure, key management, high availability and qualified legal-signature infrastructure are environment-dependent concerns and are not represented as completed capabilities unless implemented and verified.

---

## Kairo Networks

**KAIRO — Key Assurance for Integrity and Reliability of Organizations**


## Core completion

The current release treats KAIRO as an evidence lifecycle system rather than a file repository. Core controls include authenticated access, case-scoped authorization, immutable evidence versions, SHA-256 verification, chain of custody, auditable security events, a local hash-chained trust ledger, optional Hyperledger Fabric anchoring, controlled account-bound sharing, cryptographic signatures, retention/legal hold, tamper incidents, and forensic export.

Retention expiry is evaluated conservatively: an expired record becomes disposition-eligible only when no active legal hold protects it; KAIRO does not silently destroy evidence.

### Demo accounts

- `investigator` / `KairoDemo!2026`
- `forensic` / `KairoDemo!2026`
- `auditor` / `KairoDemo!2026`

These are synthetic local demonstration identities only.
