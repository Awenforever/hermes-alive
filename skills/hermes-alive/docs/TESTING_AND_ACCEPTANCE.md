# Testing and Acceptance

## Regression suites

From the installed skill or repository checkout:

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
python3 tests/run_matrix.py
python3 tests/run_stress.py
```

The matrix suite covers Provider boundaries, managed configuration precedence,
interruption policy, rich delivery, model metadata, interest learning,
transaction rollback, and uninstall behavior. The stress suite uses full scale
by default; reduced scale is only a developer smoke test.

## Joint shadow replay

The joint replay validates one deterministic path through:

1. Circadian intent recognition;
2. Circadian state and bounded learning;
3. dynamic Sleep/Quiet comparison;
4. proactive quality governance;
5. confirmed fine-grained weather context;
6. the legacy watcher delivery path.

Outside isolated acceptance, every rejection remains observe-only with
`watcher_enforced=false` and `behavior_changed=false`.

## Isolated enforcement acceptance

Delivery enforcement requires both acceptance-only environment values:

```text
HERMES_ALIVE_DELIVERY_ENFORCEMENT_MODE=isolated
HERMES_ALIVE_RUNTIME_SCOPE=isolated_test
```

Missing either value preserves observe-only behavior. Isolated enforcement is
not production readiness by itself.

## Fresh-container acceptance

Before production consideration, complete all of the following from a fresh
container and the real GitHub repository:

1. clone/install without pre-copying source into final directories;
2. complete Provider and personalization onboarding;
3. verify source, active hook, managed config, and permissions;
4. run the complete matrix and default-scale stress suites;
5. recreate the container and confirm persistent state behavior;
6. test default uninstall, reinstall, and purge with zero unexpected residue;
7. with explicit approval, use a spare WeChat account for real end-to-end
   delivery and footer verification;
8. perform a final clean uninstall.

Production source/config changes and gateway restart are separate, explicit
steps after acceptance.
