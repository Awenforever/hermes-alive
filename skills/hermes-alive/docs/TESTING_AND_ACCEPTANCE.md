# Testing and Acceptance

Reviewed 2026-10-23 (Asia/Shanghai), Codex: historical results below retain their
original date and scope; they do not qualify the current experimental kernel.
The current ordered release gates and real-platform lifecycle requirements are
in [RELEASE_ACCEPTANCE.md](RELEASE_ACCEPTANCE.md). A container fixture, simulated
Windows branch, loaded hook or model-endorsed draft is not native-platform,
consumer-installation, delivery or human usefulness acceptance. Missing gates
remain pending, including the ten consecutive fresh complete quality rounds.

## Regression suites

Kernel-3 reading-depth checks distinguish three scopes:

- `__tests__/run_public_source_refinement.py` checks the bounded decision,
  historical-cycle preservation, current/expanded source identity, revocation,
  erased evidence, oversized results and recovery without repeated IO.
- `__tests__/run_core_source_reading_depth.py --core /absolute/read-only-core`
  exercises actual guided setup, conversation confirmation, activation, Core
  model SDK and tool dispatch, and the local adapter. Run it with an explicit
  disposable `HERMES_HOME` and the intended Core-managed Python. Its public
  pages, HTTP model responses and URL-safety answers are synthetic; it proves
  wiring and preserved evidence, not factual quality or external delivery.
- A separately authorized inherited-model trial must establish useful source
  selection, faithful interpretation and natural continuation on actual public
  material. Neither a larger extract nor a model-endorsed draft proves this.

The older `kernel-setup`/`kernel-shadow` diagnostic surface cannot qualify a
feature of the ordinary configured/confirmed/activated kernel. Inspect the
actual observed mode, decisions and IO rather than assuming a CLI exit code
means an experimental flag was consumed.

From the skill root:

```bash
bash __tests__/run_all.sh
```

Focused suites:

```bash
python3 __tests__/run_circadian.py
python3 __tests__/run_circadian_shadow.py
python3 __tests__/run_circadian_intent_bridge.py
python3 __tests__/run_circadian_sleep_quiet_policy.py
python3 __tests__/run_proactive_quality_governor.py
python3 __tests__/run_location_weather_onboarding.py
python3 __tests__/run_joint_shadow_replay.py
python3 __tests__/run_isolated_enforcement.py
python3 __tests__/run_production_enforcement.py
python3 __tests__/run_discovery_quality_pivot_v3.py
python3 __tests__/run_rich_content_model_attribution_v1.py
python3 __tests__/run_runtime_disable_contract.py
python3 __tests__/run_topic_dedup_contracts.py
python3 __tests__/run_context_visibility_contracts.py
python3 __tests__/run_matrix.py
python3 __tests__/run_stress.py
```

`run_stress.py` uses contractual full scale by default. Reduced scale is a
developer smoke test and is not valid for release acceptance.

## Current mode inventory

```text
quality_governor_lifecycle_default=enforce
circadian_lifecycle_default=live
sleep_quiet_policy_live_integration=enforce
legacy_fixed_quiet_role=shadow/off_authority_and_live_comparison_fallback
isolated_delivery_enforcement=TEST_ONLY
production_feature_enforcement_readiness=SOURCE_IMPLEMENTED_PENDING_RELEASE_ACCEPTANCE
```

The inventory is a source contract only. Production completion still requires
fresh-container acceptance, release transport, controlled upgrade, restart, and
real production enforcement evidence.

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
