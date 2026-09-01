#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://127.0.0.1:8090}"

echo "[1/2] Gateway health"
curl -fsS "$BASE/health"
echo
echo "[2/2] Gateway is reachable."
echo "Next proof step: use KAIRO's Blockchain Anchor action on a verified current document."
