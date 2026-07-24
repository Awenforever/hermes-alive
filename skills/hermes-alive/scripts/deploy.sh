#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$ROOT/scripts/hermes-alive-lifecycle.py" install --source-root "$ROOT"
echo "Hermes Alive installed. Run:"
echo "  $ROOT/scripts/hermes-alive-lifecycle configure"
echo "  $ROOT/scripts/hermes-alive-lifecycle verify"
echo "Restart the gateway only after explicit approval."
