# ADR-0032: Presentation is form, not truth or authority

Status: accepted for the shadow kernel

## Context

The legacy `VoiceEngine` mixes several ontologies in one mutable
`voice_state.json`: writing-style dimensions, a guessed relationship stage,
user identity, an assistant-side social urge, ignored-message counters and
heuristic adaptations derived from vocabulary, message length, night activity
and ordinary replies. The watcher then uses the same object both to guide prose
and to label composition context.

That design makes weak behavioral correlation look like a durable user
preference. It also lets presentation state approach the decision boundary:
`social_urge` describes cadence, while `relationship_stage` presents an
inferred social fact as if it were established. Silence and an ordinary reply
are especially ambiguous and cannot prove either preference or relationship.

Current product practice usefully separates personality/characteristics from
capability and safety, and exposes user controls over remembered preferences.
Personalization research also shows that implicit identity/persona inference
can change utility and safety. The kernel therefore needs a narrower,
auditable contract rather than a more elaborate personality simulator.

## Decision

Create a replayable presentation projection whose only durable values are
bounded style dimensions. It has three provenance classes:

- `user_explicit` requires a causally linked, same-subject inbound user event
  and may affect the resolved presentation plan;
- `learned_advisory` requires accepted reflection or explicit feedback and is
  exposed for evaluation but does not automatically affect the plan; and
- `legacy_shadow` mirrors the old voice genome for comparison, expires within
  two days and never becomes active.

Missing dimensions use deterministic neutral defaults. Projection rows and
their count are installation-authenticated and rebuildable from the journal.
Corrupt state fails to neutral presentation until recovery rebuilds it.

The contract explicitly forbids truth claims, relationship inference,
semantic change, action authority and route authority. A presentation plan
always reports `permits_action = false`, `may_change_semantics = false` and
`may_choose_route = false`.

The new projection contains no user name, relationship stage, ignored count,
social urge or raw conversation. A dual-opt-in one-way bridge may pseudonymize
the delivery subject and mirror the legacy numeric dimensions. The legacy
watcher does not read the result, so production behavior remains unchanged.

## Consequences

- Explicit user style instructions can eventually survive restarts with
  provenance and correction, without becoming permission to speak.
- Silence, response timing and lexical heuristics cannot silently rewrite the
  active voice.
- Relationship and disposition require their own evidence models; they cannot
  hide inside a style profile.
- The legacy `VoiceEngine`, `social_urge` and relationship-stage prompts remain
  migration debt until shadow comparison and a semantic-fidelity evaluator
  justify removing them.
- Presentation rewriting must later prove preservation of facts, commitments,
  uncertainty, links, amounts, dates and requested action before it can join a
  live composition path.
