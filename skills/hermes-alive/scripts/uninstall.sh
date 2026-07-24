#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="uninstall"
if [[ "${1:-}" == "--purge" ]]; then
  MODE="purge"
  shift
fi
exec python3 "$ROOT/scripts/hermes-alive-lifecycle.py" "$MODE" "$@"
