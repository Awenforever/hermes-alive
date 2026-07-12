#!/usr/bin/env bash
set -Eeuo pipefail
HERMES_HOME_VALUE="${HERMES_HOME:-/opt/data}"
exec python3 "$HERMES_HOME_VALUE/skills/hermes/hermes-alive/scripts/hermes-alive-lifecycle.py" \
  configure \
  --non-interactive \
  --hermes-home "$HERMES_HOME_VALUE" \
  "$@"
