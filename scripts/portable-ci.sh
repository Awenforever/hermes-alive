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

  if "${PYTHON}" "${SKILL}/tests/${test_file}" > "${log}" 2>&1; then
    :
  else
    local test_status=$?
    cat "${log}" >&2
    printf 'portable_ci_test_failed=%s:exit=%s\n' "${test_file}" "${test_status}" >&2
    return "${test_status}"
  fi
  grep -Eq "${marker}" "${log}" || {
    cat "${log}" >&2
    printf 'portable_ci_marker_missing=%s:%s\n' "${test_file}" "${marker}" >&2
    exit 1
  }
}

run_and_require run_alive_kernel_journal.py '^HERMES_ALIVE_KERNEL_JOURNAL_OK$'
run_and_require run_alive_kernel_shadow.py '^HERMES_ALIVE_KERNEL_SHADOW_OK$'
run_and_require run_alive_kernel_retention.py '^HERMES_ALIVE_KERNEL_RETENTION_OK$'
run_and_require run_alive_kernel_consolidation.py '^HERMES_ALIVE_KERNEL_CONSOLIDATION_OK$'
run_and_require run_alive_kernel_consolidation_synthesis.py '^HERMES_ALIVE_KERNEL_CONSOLIDATION_SYNTHESIS_OK$'
run_and_require run_alive_kernel_consolidation_evaluation.py '^HERMES_ALIVE_KERNEL_CONSOLIDATION_EVALUATION_OK$'
run_and_require run_alive_kernel_recovery.py '^HERMES_ALIVE_KERNEL_RECOVERY_OK$'
run_and_require run_alive_kernel_cognition_cycle.py '^HERMES_ALIVE_KERNEL_COGNITION_CYCLE_OK$'
run_and_require run_alive_kernel_deliberation_synthesis.py '^HERMES_ALIVE_KERNEL_DELIBERATION_SYNTHESIS_OK$'
run_and_require run_alive_kernel_action_authorization.py '^HERMES_ALIVE_KERNEL_ACTION_AUTHORIZATION_OK$'
run_and_require run_action_history.py '^HERMES_ALIVE_ACTION_HISTORY_OK$'
run_and_require run_action_history_live_probe.py '^HERMES_ALIVE_ACTION_HISTORY_LIVE_PROBE_OK$'
run_and_require run_feedback_context.py '^HERMES_ALIVE_FEEDBACK_CONTEXT_OK$'
run_and_require run_send_preflight.py '^HERMES_ALIVE_SEND_PREFLIGHT_OK$'
run_and_require run_source_review_recovery.py '^HERMES_ALIVE_SOURCE_REVIEW_RECOVERY_OK$'
run_and_require run_source_scope_live_probe.py '^HERMES_ALIVE_SOURCE_SCOPE_LIVE_PROBE_OK$'
run_and_require run_reconsideration.py '^HERMES_ALIVE_RECONSIDERATION_OK$'
run_and_require run_semantic_reconsideration.py '^HERMES_ALIVE_SEMANTIC_RECONSIDERATION_OK$'
run_and_require run_feedback_assimilation.py '^HERMES_ALIVE_FEEDBACK_ASSIMILATION_OK$'
run_and_require run_commitment_cognition.py '^HERMES_ALIVE_COMMITMENT_COGNITION_OK$'
run_and_require run_communication_plan.py '^HERMES_ALIVE_COMMUNICATION_PLAN_OK$'
run_and_require run_semantic_literal_policy.py '^HERMES_ALIVE_SEMANTIC_LITERAL_POLICY_OK$'
run_and_require run_plan_order_probe.py '^HERMES_ALIVE_PLAN_ORDER_PROBE_OK$'
run_and_require run_purpose_only_probe.py '^HERMES_ALIVE_PURPOSE_ONLY_PROBE_OK$'
run_and_require run_direct_contribution_probe.py '^HERMES_ALIVE_DIRECT_CONTRIBUTION_PROBE_OK$'
run_and_require run_native_completion.py '^HERMES_ALIVE_NATIVE_COMPLETION_OK$'
run_and_require run_model_process.py '^HERMES_ALIVE_MODEL_PROCESS_OK$'
run_and_require run_native_worker_protocol.py '^HERMES_ALIVE_NATIVE_WORKER_PROTOCOL_OK$'
run_and_require run_native_host_snapshot.py '^HERMES_ALIVE_NATIVE_HOST_SNAPSHOT_OK$'
run_and_require run_native_client_policy.py '^HERMES_ALIVE_NATIVE_CLIENT_POLICY_OK$'
run_and_require run_native_host_caller.py '^HERMES_ALIVE_NATIVE_HOST_CALLER_UNIT_OK$'
run_and_require run_autonomous_host_runtime.py '^HERMES_ALIVE_AUTONOMOUS_HOST_RUNTIME_OK$'
run_and_require run_expression_history.py '^HERMES_ALIVE_EXPRESSION_HISTORY_OK$'
run_and_require run_final_wording_preparation.py '^HERMES_ALIVE_FINAL_WORDING_PREPARATION_OK$'
run_and_require run_final_wording_repair.py '^HERMES_ALIVE_FINAL_WORDING_REPAIR_OK$'
run_and_require run_shadow_final_quality.py '^HERMES_ALIVE_SHADOW_FINAL_QUALITY_OK$'
run_and_require run_alive_kernel_expression_runtime.py '^HERMES_ALIVE_KERNEL_EXPRESSION_RUNTIME_OK$'
run_and_require run_alive_kernel_opportunity_synthesis.py '^HERMES_ALIVE_KERNEL_OPPORTUNITY_SYNTHESIS_OK$'
run_and_require run_opportunity_protocol_recovery.py '^HERMES_ALIVE_OPPORTUNITY_PROTOCOL_RECOVERY_OK$'
run_and_require run_interest_recall_window.py '^HERMES_ALIVE_INTEREST_RECALL_WINDOW_OK$'
run_and_require run_alive_kernel_source_support.py '^HERMES_ALIVE_KERNEL_SOURCE_SUPPORT_OK$'
run_and_require run_source_support_history.py '^HERMES_ALIVE_SOURCE_SUPPORT_HISTORY_OK$'
run_and_require run_legacy_dream_retirement.py '^HERMES_ALIVE_LEGACY_DREAM_RETIREMENT_OK$'
run_and_require run_alive_kernel_memory.py '^HERMES_ALIVE_KERNEL_MEMORY_OK$'
run_and_require run_circadian.py '^HERMES_ALIVE_CIRCADIAN_CORE_RESULT=PASS$'
run_and_require run_circadian_shadow.py '^HERMES_ALIVE_CIRCADIAN_SHADOW_RESULT=PASS$'
run_and_require run_circadian_intent_bridge.py '^HERMES_ALIVE_CIRCADIAN_INTENT_RESULT=PASS$'
run_and_require run_circadian_sleep_quiet_policy.py '^HERMES_ALIVE_CIRCADIAN_SLEEP_QUIET_RESULT=PASS$'
run_and_require run_proactive_quality_governor.py '^HERMES_ALIVE_PROACTIVE_QUALITY_RESULT=PASS$'
run_and_require run_location_weather_onboarding.py '^HERMES_ALIVE_LOCATION_WEATHER_RESULT=PASS$'
run_and_require run_joint_shadow_replay.py '^HERMES_ALIVE_JOINT_SHADOW_REPLAY_RESULT=PASS$'
run_and_require run_isolated_enforcement.py '^HERMES_ALIVE_ISOLATED_ENFORCEMENT_RESULT=PASS$'
run_and_require run_production_enforcement.py '^HERMES_ALIVE_PRODUCTION_ENFORCEMENT_RESULT=PASS$'
run_and_require run_discovery_quality_pivot_v3.py '^HERMES_ALIVE_DISCOVERY_PIVOT_V3_RESULT=PASS$'
run_and_require run_editorial_discovery_v4.py '^HERMES_ALIVE_EDITORIAL_DISCOVERY_V4_RESULT=PASS$'
run_and_require run_bilibili_content_evidence.py '^HERMES_ALIVE_BILIBILI_CONTENT_EVIDENCE_OK$'
run_and_require run_rich_content_model_attribution_v1.py '^HERMES_ALIVE_RICH_CONTENT_MODEL_ATTRIBUTION_RESULT=PASS([[:space:]]|$)'
run_and_require run_runtime_disable_contract.py '^HERMES_ALIVE_RUNTIME_DISABLE_CONTRACT_RESULT=PASS$'
run_and_require run_plugin_cli_portable.py '^HERMES_ALIVE_PLUGIN_CLI_PORTABLE_RESULT=PASS$'
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
