#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
HOST="${1:?host required, e.g. http://192.168.1.20:8000}"
EID="${2:?evidence id required}"
VER="${3:-1}"
python3 attackvector/attack.py tamper --host "$HOST" --evidence-id "$EID" --version "$VER"
