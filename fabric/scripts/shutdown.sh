#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if [ -d "$ROOT/../work/fabric-samples/test-network" ]; then
  cd "$ROOT/../work/fabric-samples/test-network"
  ./network.sh down
else
  echo "Fabric test-network has not been downloaded yet."
fi
