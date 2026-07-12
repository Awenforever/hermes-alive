# Hermes Alive Proactive Interaction Quality Governor — Shadow v1

## Scope

This phase adds an observe-only quality layer after Circadian and Sleep/Quiet
shadow decisions. It does not replace those systems and does not alter legacy
cooldown, interruption policy, message composition, delivery, Weixin routing,
or footer metadata.

## Corrected model

User silence may create a human-like negative reaction, but only as a bounded
affective pulse:

- probabilistic, never guaranteed;
- mild intensity only;
- at most once per silence episode;
- rapidly decaying rather than accumulating;
- disabled for debug, audit, script execution, production operations, and other
  structured workflows;
- after the unanswered budget is exhausted, the recommended action is silence,
  not escalation.

## Shadow checks

The governor records what it would reject without changing delivery:

- exact and semantic near-duplicates;
- repeated task-status, presence-companion, and disappearance-affect templates;
- repeated poke/sulk/debug-companion speech acts;
- claims such as “还没跑完” without fresh structured task evidence;
- false physical or location perspective in weather wording;
- repeated affect from the same silence episode;
- affective wording when the probabilistic pulse was not selected.

## Privacy

Observability stores hashes, classifications, timestamps, bounded counters, and
an opaque silence episode identifier. Raw chat text is not persisted in the
quality state or emitted in quality-governor logs.

## Boundary

Every decision carries:

- `integration_mode=observe_only`
- `watcher_enforced=false`
- `behavior_changed=false`

The existing message is still sent even when the shadow governor says it would
reject it. Enforcement is a later isolated phase after historical replay and
matrix validation.
