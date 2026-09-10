# KAIRO

**Trust, engineered.**

KAIRO is a secure digital document and evidence lifecycle platform for legal and investigation workflows.

## Architecture

- **Frontend:** React + Vite. The repository contains the polished `Trust, engineered.` landing experience and role-aware workspace.
- **Backend:** Python + FastAPI. All protected operations are authorized server-side.
- **Database:** SQLite for the portable build; the data model is structured for PostgreSQL migration in deployment.
- **Evidence storage:** versioned filesystem objects for the portable build; use S3-compatible/WORM storage in production. PostgreSQL is metadata storage, not object storage.
- **Integrity:** SHA-256 of actual evidence bytes for every immutable version.
- **Identity:** JWT authenticated sessions with PBKDF2-SHA256 password verification.
- **Authorization:** department/role permissions plus case membership.
- **Custody & audit:** append-only audit events linked by SHA-256 hashes.
- **Recovery:** protected trusted copy per version. Restoration creates a new version and preserves the incident history.
- **Signatures:** RSA-PSS/SHA-256 over the registered evidence fingerprint.
- **Governance:** retention and legal-hold state.
- **Trust:** a pluggable trust-anchor boundary. The portable build uses a local cryptographic provider; Hyperledger Fabric is the deployment adapter, not document storage.
- **Security validation:** `attackvector/` contains the controlled storage-tamper CLI.

## Department access

| Department / role | Primary capabilities |
|---|---|
| Law Enforcement / Police | Create/manage assigned investigations, register evidence, retrieve evidence, verify integrity, controlled sharing |
| Investigative / Specialized Agency | Investigation workflow, evidence lifecycle, collaboration, verification, document intelligence, governance |
| Forensic / Scientific Laboratory | Integrity verification, version lineage, trusted restoration, signatures, forensic export, incidents, trust proofs |
| Judiciary / Legal Institution | Authorized case/evidence review and integrity verification |
| Audit / Compliance | Cross-case audit, incidents and trust oversight |
| System Administration | User/role administration and platform operations; does not automatically receive evidence-editing authority |

The UI is not the security boundary. Every protected API operation checks identity, role and case scope.

## Evidence lifecycle

`Register → fingerprint → version → custody → verify → share/sign → audit → trust-anchor`

A legitimate change creates a new version. An unauthorized storage-level modification does not become a new version; verification produces an integrity incident.

A SHA-256 mismatch proves that the observed bytes differ from the registered fingerprint. It does not, by itself, identify the attacker. Attribution requires correlation with application identity, storage access and infrastructure/security telemetry.

## Recovery model

Every registered version has:

1. an operational evidence object,
2. a registered SHA-256 fingerprint,
3. a protected recovery copy.

If the operational object is modified, KAIRO can compare it with the registered fingerprint, raise an incident, recover the verified bytes, create a new restoration version and retain the original incident/audit trail.

## Run

The supplied build is designed to run without Docker and without Node.js on the demonstration host.

Requirements: **Python 3.11+**

Windows:

```text
START_KAIRO.bat
```

macOS/Linux:

```bash
chmod +x START_KAIRO.sh
./START_KAIRO.sh
```

The server listens on port `8000` and prints its LAN address. Other laptops on the same Wi-Fi open that LAN address and use the same backend, database and evidence store.

On Windows, allow Python through the firewall on the **Private network** if prompted.

## Controlled attack validation

From another laptop:

```bash
python attackvector/attack.py tamper --host http://HOST-IP:8000 --evidence-id 1 --version 1
```

or on Windows:

```text
ATTACKVECTOR.bat http://HOST-IP:8000 1 1
```

This modifies only the selected demonstration evidence object through a protected KAIRO Security Lab endpoint. It is not an exploit against arbitrary systems.

After the simulated modification:

`Verify → Integrity mismatch → Incident → Restore trusted version → Verify again`

## Trust proof

The trust layer stores cryptographic proof, not evidence bytes.

```text
Evidence bytes
     ↓
SHA-256
     ↓
KAIRO metadata / custody / audit
     ↓
Selected trust proof
     ↓
Hyperledger Fabric adapter in deployment
```

The portable provider is intentionally used so the complete application remains runnable without Docker or a Fabric network.

## Demo identities

All included identities are synthetic:

- `police@kairo.local`
- `investigator@kairo.local`
- `forensic@kairo.local`
- `legal@kairo.local`
- `auditor@kairo.local`
- `admin@kairo.local`

Password: `KairoDemo!2026`

Demo case and documents are synthetic and should remain clearly labelled as demonstration data.

## Repository

```text
Kairo/
├── frontend/
├── backend/
├── blockchain/
├── attackvector/
├── data/
├── README.md
└── LICENSE
```

`frontend/dist/` is retained as the runnable static build so the host does not need Node.js. Frontend source changes can be rebuilt separately with Node/Vite when doing development.

## Production path

For a real deployment, replace the portable components without changing the evidence lifecycle:

`SQLite → PostgreSQL`

`filesystem objects → S3-compatible/WORM object storage`

`local trust provider → Hyperledger Fabric network`

and add institutional SSO/MFA, managed secrets/keys, TLS, centralized security telemetry, hardened storage policies and deployment-specific compliance controls.
