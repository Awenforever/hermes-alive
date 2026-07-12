# Circadian Engine Core V1

This phase adds an isolated deterministic core only. It does not change production, watcher delivery, managed configuration, or Weixin behaviour.

## Ownership boundary

- `circadian_engine.py` owns planned/actual sleep and wake facts, phases, sleep debt, learned offsets, persistence, and shadow decisions.
- Interruption policy will consume the decision in a later integration phase.
- Voice/LLM will receive only structured facts in a later integration phase and must not invent sleep history.

## Default contract

- Timezone: `Asia/Singapore`
- Preferred sleep: `23:00`
- Preferred wake: `07:00`
- Mode: `shadow`
- State: `hermes_alive_shared/circadian_state.json`
- Hard exemptions: system errors, service/security alerts, control commands, explicit reminders, Email Watchdog, and business-critical notifications.
