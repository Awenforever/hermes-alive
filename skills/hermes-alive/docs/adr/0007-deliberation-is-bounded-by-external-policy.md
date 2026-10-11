# ADR-0007: Deliberation is bounded by external policy

- Status: accepted for kernel shadow development
- Date: 2026-10-10
- Depends on: ADR-0001, ADR-0006

## Context

A single hand-tuned “proactivity score” hides incompatible concerns and makes
unsafe behavior difficult to diagnose. Letting a language model both propose
and authorize an action is worse: persuasive reasoning can silently relax
privacy, interruption or side-effect constraints. Conversely, rules alone are
poor at comparing several context-dependent, qualitatively different choices.

## Decision

Every deliberation frame contains multiple typed action candidates and a real
`silence` candidate. Each non-silence candidate carries separate assessments
for user value, urgency, novelty, confidence, interruption cost and risk, plus
an explicit authority class. Every assessment cites durable evidence and says
whether it came from measurement, a user rule or a model judgment.

Deterministic policy runs before model deliberation. It rejects candidates that
exceed risk, lack confidence or authority, interrupt a protected period, or ask
for a side effect outside the current capability grant. Rejection reasons stay
separate and inspectable. The policy does not collapse dimensions into a magic
weighted score.

The model may choose only among the surviving candidate IDs and must return a
structured selection with a rationale. A second deterministic check rejects an
unknown, filtered or mutated ID. Silence can always be selected and is the
default when no actionable candidate survives or model output is invalid.

Evidence and agenda references are also subject-scoped. A frame may cite only
evidence belonging to its subject or a genuinely subject-neutral system event.
An `agenda_item_id`, when present, must resolve to an active item owned by the
same subject. A real but foreign agenda item is rejected just like a missing
one; identity boundaries are not left to model judgment.

## Consequences

- Fluent model text cannot grant permission or reduce measured risk.
- Changing a threshold does not rewrite the underlying assessments.
- Replays can distinguish candidate generation, policy rejection and model
  choice instead of treating them as one opaque answer.
- Later evaluators can measure whether silence or interruption was correct.

The implemented durable projection re-runs policy when loading a frame, stores
private reasons and model rationale in the erasable content vault, and records
both accepted and rejected selections. Provider calls and production shadow
comparison remain separate gates.
