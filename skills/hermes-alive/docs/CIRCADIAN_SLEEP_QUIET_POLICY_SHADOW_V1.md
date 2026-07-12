# Circadian Sleep / Quiet Policy Shadow V1

This phase compares the deterministic Circadian Engine with the existing fixed quiet-hours gate. It is **observe-only** and does not change outbound behaviour.

## Policy ownership

- Circadian Engine owns dynamic sleep facts: winding down, drowsy, asleep, light sleep, forced awake, sleep debt and recovery.
- `CooldownManager` remains the authoritative production quiet-hours and cooldown gate in this phase.
- The new shadow policy records where dynamic sleep protection and fixed quiet-hours agree or disagree.
- Control-queue system messages are still processed before all social sleep/quiet evaluation.

## Dynamic shadow rules

Normal proactive-social messages would be protected during:

- winding down
- drowsy
- asleep
- light sleep

They would be allowed while awake, forced awake, sleep deprived, overslept or recovering. Unknown phases fail open because this phase is not allowed to become an accidental delivery block.

Hard-exempt message classes remain allowed:

- system errors
- service and security alerts
- control commands
- explicit reminders
- Email Watchdog notifications
- business-critical notifications

## Comparison outcomes

Each eligible social tick records one of:

- `aligned_allow`
- `aligned_block`
- `dynamic_more_protective`
- `dynamic_more_permissive`
- `hard_exempt_bypass`

The record includes fixed quiet start/end, local evaluation minute, Circadian phase, planned sleep/wake time and sleep debt. It stores no raw chat message or secret.

## Safety boundary

- `watcher_enforced=false`
- `behavior_changed=false`
- no message is blocked or sent by this module
- existing fixed quiet-hours remain authoritative
- no sleep/wake transition message is generated
- production source, active hook, config and state are not modified by the development script
