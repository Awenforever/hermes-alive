#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/run_matrix.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/run_stress.py"
echo HERMES_ALIVE_PHASE_H_ALL_RESULT=PASS
