# ADR-0011: Exploration can only narrow already-safe options

- Status: accepted for kernel shadow development
- Date: 2026-10-10
- Depends on: ADR-0007, ADR-0008, ADR-0010

## Context

Pure exploitation creates a filter bubble, but naïve exploration turns users
into test subjects and can increase interruption. Diversity is also easy to
fake by rotating labels while repeatedly using the same source or semantic
lane. A random exploration bonus must never offset risk, missing authority or a
protected quiet period.

## Decision

Exploration is a second deterministic gate applied only after the base policy.
It can remove candidates but cannot admit a candidate rejected for safety,
authority, confidence, side effects or interruption. Deliberate silence always
survives.

Each actionable candidate receives an encrypted topic/source annotation and
structural keyed digests. It is marked `exploit` or `explore`; this describes
why it is considered, not whether it is safe. The gate enforces a rolling
exploration count, maximum topic and source shares after a minimum sample size,
and a maximum same-topic streak. All rejection reasons remain separate.

Only observed successful deliveries enter exposure history. Attempts, model
selections, failed sends and silence do not count as exposure. Exploration is
therefore constrained by what the user could actually have seen.

## Consequences

- Diversity cannot bypass the primary safety policy.
- Exploration has a hard, inspectable budget rather than a hidden novelty bonus.
- Topic and source labels remain private while repetition is measurable.
- Missing annotations fail closed for action candidates, never for silence.
- Encrypted annotations and recomputable gate receipts are persisted. Every
  non-silence selection must causally cite an earlier admissible receipt;
  bypass attempts are rejected. Production shadow integration remains gated.
