# Hyperledger Fabric integration

KAIRO includes a real Fabric Gateway integration path rather than a simulated blockchain response.

Current implementation:

- Hyperledger Fabric test-network compatible deployment scripts
- `mychannel` channel
- `kairo-trust` chaincode
- JavaScript chaincode
- Node.js Fabric Gateway service
- Anchor, read and health operations
- On-chain transaction ID returned by Fabric

Anchor records contain proof-oriented fields such as document ID, version, evidence hash, custody digest, actor, action and timestamp.

Documents themselves remain off-chain.

The local Fabric network and gateway must be running before KAIRO can produce a live Fabric anchor. KAIRO must never display a successful blockchain transaction when the gateway is unavailable.
