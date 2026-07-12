# Test Guide

Run the complete regression suite:

```bash
bash tests/run_all.sh
```

Run focused suites from the skill root:

```bash
python3 tests/run_circadian.py
python3 tests/run_circadian_shadow.py
python3 tests/run_circadian_intent_bridge.py
python3 tests/run_circadian_sleep_quiet_policy.py
python3 tests/run_proactive_quality_governor.py
python3 tests/run_location_weather_onboarding.py
python3 tests/run_joint_shadow_replay.py
python3 tests/run_isolated_enforcement.py
python3 tests/run_matrix.py
python3 tests/run_stress.py
```

`run_stress.py` uses contractual full scale by default. A reduced developer
smoke run may be requested with:

```bash
HERMES_ALIVE_STRESS_SCALE=0.05 python3 tests/run_stress.py
```

Reduced scale is not valid for final acceptance. See
`../docs/TESTING_AND_ACCEPTANCE.md` for the fresh-container and real-WeChat
acceptance sequence.
