#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/run_circadian.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/run_circadian_shadow.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/run_circadian_intent_bridge.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/run_circadian_sleep_quiet_policy.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/run_proactive_quality_governor.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/run_location_weather_onboarding.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/run_joint_shadow_replay.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/run_isolated_enforcement.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/run_discovery_quality_pivot_v3.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/run_rich_content_model_attribution_v1.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/run_matrix.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ROOT/tests/run_stress.py"
echo HERMES_ALIVE_PHASE_H_ALL_RESULT=PASS
