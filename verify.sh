#!/usr/bin/env bash
set -Eeuo pipefail
HERMES_HOME_VALUE="${HERMES_HOME:-/opt/data}"
exec python3 "$HERMES_HOME_VALUE/skills/hermes/hermes-alive/scripts/hermes-alive-lifecycle.py" \
  verify \
  --hermes-home "$HERMES_HOME_VALUE" \
  "$@"
