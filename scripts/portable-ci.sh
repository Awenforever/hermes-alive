#!/usr/bin/env bash
set -Eeuo pipefail
umask 022

ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="${ROOT}/skills/hermes-alive"
PYTHON="${PYTHON:-python3}"

CI_HOME="${HERMES_ALIVE_CI_HOME:-${HOME}/.cache/hermes-alive-portable-ci}"
BIN="${CI_HOME}/bin"
PYCACHE="${CI_HOME}/pycache"
SHARED="${CI_HOME}/hermes_alive_shared"

rm -rf "${CI_HOME}"
mkdir -p "${BIN}" "${PYCACHE}" "${SHARED}"

cat > "${BIN}/hermes" <<'SH'
#!/bin/sh
set -u
if [ "${1:-}" = "config" ] && [ "${2:-}" = "path" ]; then
  printf '%s\n' "${HERMES_HOME}/config.yaml"
  exit 0
fi
if [ "${1:-}" = "setup" ] && [ "${2:-}" = "model" ]; then
  exit 0
fi
if [ "${1:-}" = "skills" ]; then
  exit 0
fi
exit 0
SH
chmod 0755 "${BIN}/hermes"
printf '%s\n' 'model: fake-provider/fake-model' > "${CI_HOME}/config.yaml"

export HOME="${CI_HOME}"
export HERMES_HOME="${CI_HOME}"
export HERMES_ALIVE_SHARED_DIR="${SHARED}"
export HERMES_CLI="${BIN}/hermes"
export PATH="${BIN}:${PATH}"
export PYTHONPATH="${ROOT}/ci/fakes:${SKILL}/hooks:${SKILL}/tests"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPYCACHEPREFIX="${PYCACHE}"
export HERMES_ALIVE_TEST_MODE=1
export HERMES_ALIVE_DISABLE_PROVIDER=1
export HERMES_ALIVE_DISABLE_WEIXIN_SEND=1
export HERMES_ALIVE_ENFORCEMENT_TEST_MODE=1

"${PYTHON}" "${ROOT}/scripts/verify-repository.py" --root "${ROOT}"

"${PYTHON}" -m compileall -q -f "${SKILL}"

run_and_require() {
  local test_file="$1"
  local marker="$2"
  local log="${CI_HOME}/$(basename "${test_file}").log"

  "${PYTHON}" "${SKILL}/tests/${test_file}" > "${log}" 2>&1
  grep -Eq "${marker}" "${log}" || {
    cat "${log}" >&2
    printf 'portable_ci_marker_missing=%s:%s\n' "${test_file}" "${marker}" >&2
    exit 1
  }
}

run_and_require run_circadian.py '^HERMES_ALIVE_CIRCADIAN_CORE_RESULT=PASS$'
run_and_require run_circadian_shadow.py '^HERMES_ALIVE_CIRCADIAN_SHADOW_RESULT=PASS$'
run_and_require run_circadian_intent_bridge.py '^HERMES_ALIVE_CIRCADIAN_INTENT_RESULT=PASS$'
run_and_require run_circadian_sleep_quiet_policy.py '^HERMES_ALIVE_CIRCADIAN_SLEEP_QUIET_RESULT=PASS$'
run_and_require run_proactive_quality_governor.py '^HERMES_ALIVE_PROACTIVE_QUALITY_RESULT=PASS$'
run_and_require run_location_weather_onboarding.py '^HERMES_ALIVE_LOCATION_WEATHER_RESULT=PASS$'
run_and_require run_joint_shadow_replay.py '^HERMES_ALIVE_JOINT_SHADOW_REPLAY_RESULT=PASS$'
run_and_require run_isolated_enforcement.py '^HERMES_ALIVE_ISOLATED_ENFORCEMENT_RESULT=PASS$'
run_and_require run_discovery_quality_pivot_v3.py '^HERMES_ALIVE_DISCOVERY_PIVOT_V3_RESULT=PASS$'
run_and_require run_rich_content_model_attribution_v1.py '^HERMES_ALIVE_RICH_CONTENT_MODEL_ATTRIBUTION_RESULT=PASS([[:space:]]|$)'
run_and_require run_runtime_disable_contract.py '^HERMES_ALIVE_RUNTIME_DISABLE_CONTRACT_RESULT=PASS$'
run_and_require run_context_visibility_contracts.py '^safe_context_observability=PASS$'
run_and_require run_topic_dedup_contracts.py '^watcher_pre_each_send_guards=PASS$'
run_and_require run_matrix.py '^HERMES_ALIVE_MATRIX_RESULT=PASS$'

HERMES_ALIVE_STRESS_SCALE="${HERMES_ALIVE_STRESS_SCALE:-0.05}" \
  "${PYTHON}" "${SKILL}/tests/run_stress.py" \
  > "${CI_HOME}/run_stress.py.log" 2>&1
grep -q '^HERMES_ALIVE_STRESS_RESULT=PASS$' \
  "${CI_HOME}/run_stress.py.log" || {
    cat "${CI_HOME}/run_stress.py.log" >&2
    exit 1
  }

printf 'HERMES_ALIVE_PORTABLE_CI_RESULT=PASS\n'
printf 'runtime_only_full_acceptance_required=true\n'
