# KAIRO Final UI + Backend Fixes

## Auditor workspace

- Auditors have read-only oversight of the case registry and evidence metadata.
- Auditor dashboard counts include all cases/documents/versions available for audit oversight.
- Auditor search can retrieve metadata across the audit-visible case set.
- Auditor incident visibility is global and remains read-only.
- Auditors cannot gain write access through the case-access exception.

## Audit trail

- Audit rows are explicitly labeled as `Evidence / custody event` when the event belongs to the evidence lifecycle.
- The previous unexplained chevron is now a purposeful `View details` action.
- Selecting an event opens a detail panel showing actor, result, target, target ID, timestamp, event ID and recorded details.
- Security/governance events are distinguished from evidence/custody events.

## Visual system

- Preserved the existing light Swiss/Apple-inspired visual language.
- Preserved the blue-to-green trust gradient used by the strongest Trust Ledger and Integrity surfaces.
- Added the same restrained trust treatment to the audit explanation without introducing a new visual system.
- Changed the Trust Ledger statistic from `Chain height` to `Latest index` so the UI does not imply that PostgreSQL sequence gaps are chain-height gaps.

## Backend safety

- Case-level authorization remains enforced for investigators/forensic users.
- Auditor read-only access is explicitly separated from write access.
- Existing JWT/RBAC and case membership enforcement remain intact.
