# Circadian Shadow Integration V1

This phase integrates the deterministic Circadian Engine into managed configuration and the proactive watcher in **observe-only shadow mode**.

## Safety boundary

- The watcher records a `circadian_shadow` decision for normal proactive-social ticks.
- The decision is never enforced in this phase, including if external configuration incorrectly says `live`.
- Control-queue system messages are processed before Circadian evaluation and remain hard-exempt.
- Existing fixed quiet-hours, cooldown, interruption policy, delivery, Weixin routing and footer behavior remain authoritative.
- No sleep/wake transition message is generated.

## Managed configuration

The lifecycle schema is version 2 and includes the complete Circadian configuration contract. Defaults are:

- enabled: true
- mode: shadow
- timezone: Asia/Singapore
- base sleep: 23:00
- base wake: 07:00

All Circadian values are exported through `HERMES_ALIVE_CIRCADIAN_*` environment variables by the managed configuration loader. Provider secrets are neither read nor stored by this feature.

## Observability

Each eligible watcher tick may record:

- phase
- planned sleep/wake timestamps
- sleep debt
- dynamic sleep/deep-core decision
- whether the message class is hard-exempt
- `watcher_enforced=false`
- `behavior_changed=false`

The state is stored only at `hermes_alive_shared/circadian_state.json`.
