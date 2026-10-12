# ADR-0033: Disposition is post-selection expression, not synthetic emotion

Status: accepted for the shadow kernel

## Context

The legacy runtime stores hand-tuned `energy`, `boredom`, `annoyance`,
`affection`, `curiosity` and `pressure` values. `proactive_disposition.py`
blends those values with a mutable social urge, inferred relationship stage,
voice dimensions, unanswered-message pressure and fixed coefficients to decide
whether to speak, which acts to use and how many bubbles to emit.

Even when the arithmetic is bounded, the ontology is wrong. Non-response is
not annoyance. Time passage is not boredom. A guessed relationship stage is
not authority. A single weighted willingness score also hides which evidence
actually changed an external action.

The kernel already evaluates each candidate along independently evidenced
value, urgency, novelty, confidence, interruption cost and risk dimensions,
then validates a selection under separate policy. Reusing those audited facts
after selection is more explainable than creating another persistent emotion
model before it.

## Decision

A disposition is an immutable, authenticated expression snapshot derived only
after an exact selection has been validated. It cannot participate in candidate
admission or selection. Each cue is a direct interpretation of one existing
decision dimension and retains that dimension's evidence IDs:

- material risk suggests `careful`;
- high interruption cost suggests `gentle`;
- high urgency suggests `focused`;
- grounded novelty suggests `curious`; and
- an otherwise communicative action uses neutral `steady` expression.

There is no blended disposition score. Silence and non-communication actions
have no renderable disposition. Snapshots explicitly deny emotion claims,
relationship inference, interpretation of silence, action authority, selection
changes and semantic changes.

The recorder verifies the same-subject selection event, latest validated intent
and stored candidate before writing. Consumers must re-authenticate the payload
and recompute every cue from the selected candidate before use. The snapshot
contains no candidate plaintext or model rationale.

## Consequences

- Expression can eventually respond to why an already authorized message is
  delicate or urgent without letting style decide that the message exists.
- “Annoyed because ignored” and similar pseudo-emotions have no representation
  in the new contract.
- Thresholds remain explicit policy constants and require replay evaluation;
  they are not claims about an inner emotional state.
- The legacy mood/disposition path remains live migration debt. The new
  snapshot is unscheduled and cannot affect production until a semantic-
  fidelity renderer and shadow comparison qualify it.
