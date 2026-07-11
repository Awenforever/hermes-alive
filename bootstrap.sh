#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$ROOT/skills/hermes-alive"
test -f "$SKILL_ROOT/SKILL.md"
exec python3 "$SKILL_ROOT/scripts/hermes-alive-lifecycle.py" \
  install \
  --source-root "$SKILL_ROOT" \
  "$@"
