# Testing and Acceptance

## Regression suites

From the skill root:

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
python3 tests/run_matrix.py
python3 tests/run_stress.py
```

`run_stress.py` uses contractual full scale by default. Reduced scale is a
developer smoke test and is not valid for release acceptance.

## Current mode inventory

```text
quality_governor_lifecycle_default=enforce
circadian_lifecycle_default=shadow
sleep_quiet_policy_integration=observe_only
isolated_delivery_enforcement=TEST_ONLY
production_feature_enforcement_readiness=INCOMPLETE_SHADOW_COMPONENTS_REMAIN
```

A passing inventory means the documentation accurately describes these modes. It
does not convert shadow components into production enforcement.

## Verified isolated acceptance

On July 24, 2026, the current source passed an isolated acceptance using the
local Hermes production image with `--pull never`, `network none`, a read-only
candidate mount, direct Hermes venv Python, and no executable dependency under
`/tmp`.

Verified gates included:

- exact source hashes and clean release candidate;
- Python compilation;
- URL/topic canonicalization, corruption recovery, concurrency, privacy, and
  material-update hardening;
- cached-candidate rotation, exhaustion without replay, restart persistence, and
  material-update re-entry;
- complete regression, model attribution, matrix, and default-scale stress;
- fresh install, idempotent install, non-interactive configuration, and verify;
- installed-source and active-hook hash alignment;
- persistence across container recreation;
- uninstall preserving shared state and removing code;
- reinstall after uninstall;
- installed topic, rotation, context, and mode contracts;
- purge with zero residue;
- reinstall after purge and final purge;
- container/volume cleanup;
- unchanged production snapshot and unchanged `weixin.py`.

No Provider call or real WeChat message occurred.

## Acceptance-only dual-key enforcement

Combined dynamic enforcement tests require both:

```text
HERMES_ALIVE_DELIVERY_ENFORCEMENT_MODE=isolated
HERMES_ALIVE_RUNTIME_SCOPE=isolated_test
```

Missing either value keeps that acceptance-only path disabled. This guard is not
a production-readiness claim.

## Remaining release gates

Isolated source/lifecycle acceptance is a release gate, not final completion.
The remaining sequence is:

1. build the complete repository candidate with root README files,
   `skills/hermes-alive`, metadata, bootstrap, and Actions;
2. verify bare/bundle transport from Git objects rather than a pre-copied tree;
3. install from a real GitHub URL in a fresh container;
4. with explicit approval, run spare-WeChat end-to-end delivery and footer tests;
5. request explicit production deployment approval;
6. deploy through a controlled, reversible production procedure;
7. verify intended production mode activation;
8. observe production stability across quiet-hour crossings, Discovery cycles,
   Provider failure/recovery, container restart, and NAS restart.

Final completion requires production behavior and persistence to match the
documented design. Shadow or observe-only modules cannot be counted as enforced
production features.
