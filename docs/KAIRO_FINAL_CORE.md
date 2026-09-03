# KAIRO Core

KAIRO is a secure digital document and evidence lifecycle platform for legal and investigation workflows.

## Core lifecycle

Case → controlled upload → immutable version → SHA-256 fingerprint → verification → custody → audit → local trust chain → optional Fabric anchor → controlled retrieval/export.

## Security model

Identity is authenticated before protected actions. Role permissions are evaluated server-side, then case membership scopes access to the assigned investigation. Denied operations are auditable. Evidence bytes are never accepted as trustworthy merely because a filename or UI state says so.

## Evidence governance

Retention and legal hold are persistent governance state. A retention scan marks expired, unheld records as eligible for disposition; it does not silently destroy evidence.

## Blockchain

Sensitive evidence bytes remain off-chain. Fabric stores a proof record containing document/version identity, evidence SHA-256, custody digest, actor, action, timestamp and Fabric transaction ID.

## Local demo identities

- `investigator` / `KairoDemo!2026`
- `forensic` / `KairoDemo!2026`
- `auditor` / `KairoDemo!2026`

All demo data and identities are synthetic.
