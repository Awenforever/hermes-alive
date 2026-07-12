# Circadian Joint Shadow Replay V1

Markers:

- `HERMES_ALIVE_CIRCADIAN_JOINT_SHADOW_REPLAY_V1`
- `HERMES_ALIVE_JOINT_REPLAY_PRIVACY_BOUNDARY_V1`
- `HERMES_ALIVE_JOINT_REPLAY_NO_ENFORCEMENT_V1`

## Purpose

This phase validates the already implemented shadow components as one coherent path before any isolated enforcement is introduced. It adds deterministic replay tests and documentation only; it does not change runtime decision code.

Replay order:

1. Circadian Intent & State Bridge
2. Circadian Engine state and learning
3. Sleep / Quiet Policy comparison
4. Proactive Quality Governor
5. Confirmed fine-grained location and weather perspective
6. Existing watcher delivery path

## Covered scenarios

- explicit goodnight enters winding-down and dynamic sleep protection;
- pending sleep transitions into asleep/light-sleep;
- Email Watchdog and other hard exemptions bypass social sleep protection;
- `再陪我一会儿` creates a bounded temporary `forced_awake` state;
- `醒醒` creates forced wake and sleep debt;
- user observations such as `我还在忙` do not mutate Hermes' sleep state;
- repeated late interaction learning is slow and bounded by daily/weekly limits;
- one silence episode can produce at most one mild probabilistic affective pulse;
- exhausted unanswered budget recommends silence rather than escalation;
- debug/script workflows do not interpret silence as rejection;
- the historical 17-message repetition sequence is collapsed by semantic, family and speech-act cooldowns;
- confirmed district/county-equivalent weather context is accepted while fake robot physical experience is rejected;
- the watcher records Circadian, Sleep/Quiet and Quality shadow rejection but still follows the legacy send path.

## Enforcement boundary

Every new replay assertion requires:

- `watcher_enforced=false`;
- `behavior_changed=false`;
- existing fixed quiet-hours remain authoritative;
- quality rejection remains observe-only;
- no production source, active hook, managed config or runtime state is changed;
- no real Weixin or email message is sent.

## Privacy

Replay state is created in throw-away private directories. Raw private sentinels must not appear in intent bridge state, Circadian state, quality state or replay evidence.

## Next step

After this phase passes on the NAS host and isolated development container, the next mainline phase is isolated enforcement design and implementation. Enforcement must remain outside production and must preserve hard exemptions, footer attribution, control-queue ordering and lifecycle safety.
