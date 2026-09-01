# KAIRO Trust Anchor — Hyperledger Fabric

This directory contains the **real permissioned-ledger integration layer** for KAIRO. Sensitive evidence bytes are NOT stored on-chain. KAIRO anchors a cryptographic proof containing the document/version hash and a custody digest.

## Architecture

KAIRO API → Fabric Gateway → Hyperledger Fabric peer → `kairo-trust` chaincode → permissioned ledger

## What is actually on-chain

- KAIRO anchor ID
- document number/id
- version
- evidence SHA-256
- custody digest
- authenticated actor identity label
- action
- timestamp
- Fabric transaction ID

The actual document remains in MinIO.

## Setup

The scripts use the official Hyperledger Fabric test-network from `fabric-samples`. They are intended for a local SIH demonstration, not production deployment.

Prerequisites: Docker Desktop, WSL2, Git, Node.js 18+.

From WSL:

```bash
cd /mnt/c/Developer/Kairo/fabric/scripts
chmod +x bootstrap.sh
./bootstrap.sh
```

After the network is running, start the gateway:

```bash
cd /mnt/c/Developer/Kairo/blockchain-gateway
npm install
node server.js
```

The gateway listens on `http://127.0.0.1:8090`.

KAIRO's API can then use the gateway by setting:

`KAIRO_BLOCKCHAIN_URL=http://127.0.0.1:8090`

If the gateway/network is unavailable, KAIRO does **not** pretend the anchor was written to blockchain; the API reports the integration as unavailable.
