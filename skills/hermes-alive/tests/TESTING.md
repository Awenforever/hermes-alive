# Test Guide

Run the complete regression suite:

```bash
bash tests/run_all.sh
```

Focused suites:

```bash
python3 tests/run_circadian.py
python3 tests/run_circadian_shadow.py
python3 tests/run_circadian_intent_bridge.py
python3 tests/run_circadian_sleep_quiet_policy.py
python3 tests/run_proactive_quality_governor.py
python3 tests/run_location_weather_onboarding.py
python3 tests/run_joint_shadow_replay.py
python3 tests/run_isolated_enforcement.py
python3 tests/run_discovery_quality_pivot_v3.py
python3 tests/run_rich_content_model_attribution_v1.py
python3 tests/run_runtime_disable_contract.py
python3 tests/run_topic_dedup_contracts.py
python3 tests/run_context_visibility_contracts.py
python3 tests/run_context_visibility_concurrency_replay.py
python3 tests/run_personality_semantic_bubbles.py
python3 tests/run_personality_semantic_stress_replay.py
python3 tests/run_matrix.py
python3 tests/run_stress.py
```

`run_stress.py` uses contractual full scale by default:

```bash
python3 tests/run_stress.py
```

A reduced developer smoke run may be requested with:

```bash
HERMES_ALIVE_STRESS_SCALE=0.05 python3 tests/run_stress.py
```

Reduced scale is not valid for final acceptance.

The expected complete-suite marker is:

```text
HERMES_ALIVE_PHASE_H_ALL_RESULT=PASS
```

See `../docs/TESTING_AND_ACCEPTANCE.md` for isolated lifecycle, repository
transport, real GitHub URL, spare-WeChat E2E, and production acceptance gates.
