#!/usr/bin/env bash
set -euo pipefail
for cmd in docker git node npm; do command -v "$cmd" >/dev/null && echo "OK   $cmd" || echo "MISS $cmd"; done
docker info >/dev/null 2>&1 && echo "OK   Docker daemon" || echo "MISS Docker daemon"
[ -d "$(cd "$(dirname "$0")/../work" && pwd)/fabric-samples/test-network" ] && echo "OK   fabric-samples" || echo "MISS fabric-samples (run bootstrap.sh)"
