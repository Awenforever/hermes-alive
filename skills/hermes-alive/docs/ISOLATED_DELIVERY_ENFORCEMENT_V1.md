# Isolated Delivery Enforcement v1

Markers:

- `HERMES_ALIVE_ISOLATED_ENFORCEMENT_V1`
- `HERMES_ALIVE_ISOLATED_ENFORCEMENT_DUAL_KEY_GUARD_V1`
- `HERMES_ALIVE_ISOLATED_DELIVERY_ENFORCEMENT_V1`
- `HERMES_ALIVE_QUALITY_COMMIT_AFTER_DELIVERY_V1`

## Scope

This phase converts previously validated Circadian, Sleep / Quiet and
Proactive Quality shadow decisions into real delivery controls only inside the
isolated development runtime.

Enforcement requires both environment values:

```text
HERMES_ALIVE_DELIVERY_ENFORCEMENT_MODE=isolated
HERMES_ALIVE_RUNTIME_SCOPE=isolated_test
```

Neither value is exposed through managed configuration. Missing or different
values preserve the previous observe-only behavior.

## Enforced behavior

- Control-queue messages continue to bypass all social gates.
- Dynamic sleep protection can stop composition before any proactive message is
  generated.
- A user-forced awake state can override the legacy fixed quiet-hours gate only
  in the isolated runtime.
- The unanswered-message silence lock stops composition.
- Candidate messages rejected by the quality governor are removed before
  delivery.
- Missing candidate audits fail closed only in isolated enforcement.
- Accepted affective pulses are committed only after successful delivery.
- Rejected message bodies are not written into enforcement observability.

## Non-goals

- No production source, active hook, config, state, container or message is
  modified.
- No production-facing configuration switch is introduced.
- No provider, footer, Weixin routing or control-message behavior is changed.
- This phase does not yet constitute fresh-container installation acceptance.
