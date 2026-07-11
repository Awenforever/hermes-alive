#!/usr/bin/env bash
set -Eeuo pipefail
HERMES_HOME_VALUE="${HERMES_HOME:-/opt/data}"
MODE="uninstall"
if [[ "${1:-}" == "--purge" ]]; then
  MODE="purge"
  shift
fi
exec python3 "$HERMES_HOME_VALUE/skills/hermes/hermes-alive/scripts/hermes-alive-lifecycle.py" \
  "$MODE" \
  --hermes-home "$HERMES_HOME_VALUE" \
  "$@"
