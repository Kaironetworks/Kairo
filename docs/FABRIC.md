# Real Hyperledger Fabric — next update

Use a real Fabric network, not a Python/JSON/mock ledger.

Recommended:
- multiple Fabric organizations for stakeholder separation
- real channel
- Go chaincode
- Node/TypeScript Fabric Gateway client

On-chain records:
document ID, case ID, version, SHA-256, event type, actor identity, timestamp, object reference and relevant proof metadata.

Documents themselves remain off-chain.
