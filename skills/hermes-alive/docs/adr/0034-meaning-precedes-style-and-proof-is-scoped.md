# ADR-0034: Meaning precedes style and fidelity proof is scoped

Status: accepted for the shadow kernel

## Context

Presentation policy and post-selection disposition are safe only if changing
form cannot silently alter meaning. Dates, amounts, links, contacts, negation,
uncertainty, caveats, attribution and requested actions are particularly easy
to omit or distort during free-form rewriting.

Strict structured output can constrain a model's JSON shape, but it does not
prove that generated content is supported or semantically equivalent. Text
style transfer research likewise treats style accuracy, content preservation
and naturalness as separate dimensions, and finds that automatic preservation
metrics have inconsistent or insufficient validation. Letting one model write
and self-certify therefore cannot be a production trust boundary.

## Decision

Introduce an encrypted meaning document before rendering. It contains bounded,
ordered semantic atoms with source event IDs. Deadline, amount, link, contact,
uncertainty and negation atoms must declare exact protected literals. The
journal stores only atom IDs/kinds, evidence IDs and an encrypted content
reference; raw atom text remains in the erasable content vault.

A deliberation candidate must bind the exact meaning event through a strict
reference-only candidate document. Rendering is allowed only after that
candidate is the latest validated same-subject communication selection.

Two renderer classes are deliberately different:

- `deterministic` emits every atom verbatim and changes formatting separators
  only. Exact reconstruction can prove transformation fidelity.
- `model_candidate` can never self-promote to proven. Missing locked literals
  are rejected; ordinary atom text that changed or was paraphrased remains
  `review_required` for the independent boundary defined in ADR-0035.

Fidelity proof is narrowly scoped. It proves that deterministic rendering did
not change the defined meaning. It does not prove that the meaning is true,
that evidence entails every atom, that an action is authorized, or that a
route may be used. Events state those non-claims explicitly.

Render receipts are installation-authenticated, content-vault backed and bound
to the exact latest validated selection. A newer validated selection
invalidates an older receipt even when it selects the same candidate.

## Consequences

- Production always has a non-generative, semantically lossless rendering
  baseline.
- Model rewriting remains possible as research, but cannot be confused with a
  delivery-ready result because it happens to satisfy a schema or preserve a
  few literals.
- Factuality/entailment, semantic fidelity, action authority and routing remain
  four independent proof obligations.
- Before model-rendered prose can enter a canary, exercise the ADR-0035
  independent-review contract over a qualification-sized multilingual corpus
  with human-calibrated thresholds. No single similarity score may close that
  gate.
