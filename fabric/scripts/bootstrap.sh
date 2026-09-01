#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
WORK="${ROOT}/../work"
mkdir -p "$WORK"
cd "$WORK"
command -v docker >/dev/null || { echo "Docker is required."; exit 1; }
command -v git >/dev/null || { echo "Git is required inside WSL."; exit 1; }
if [ ! -d fabric-samples ]; then git clone --depth 1 https://github.com/hyperledger/fabric-samples.git; fi
cd fabric-samples/test-network
./network.sh down >/dev/null 2>&1 || true
./network.sh up createChannel -ca
CC_SRC="${ROOT}/../chaincode/kairo-trust"
./network.sh deployCC -ccn kairo-trust -ccp "$CC_SRC" -ccl javascript
echo
echo "KAIRO Fabric network is READY"
echo "Channel: mychannel"
echo "Chaincode: kairo-trust"
echo "Peer: localhost:7051"
