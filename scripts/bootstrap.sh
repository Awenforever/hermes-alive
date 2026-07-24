#!/usr/bin/env bash
set -Eeuo pipefail
umask 022

ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="${ROOT}/skills/hermes-alive"

if [ ! -f "${SKILL}/SKILL.md" ]; then
  printf 'repository_error=missing_skill_root\n' >&2
  exit 2
fi

bash "${SKILL}/scripts/install.sh"

"${SKILL}/scripts/hermes-alive-lifecycle" configure \
  --non-interactive \
  --enable \
  --skip-weather \
  "$@"

bash "${SKILL}/scripts/verify.sh"

printf 'HERMES_ALIVE_REPOSITORY_BOOTSTRAP_OK\n'
