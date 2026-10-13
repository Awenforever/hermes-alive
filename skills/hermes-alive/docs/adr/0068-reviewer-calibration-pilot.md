# ADR 0068 — Measure reviewer errors before trusting positive verdicts

Status: accepted for isolated experiments; no production admission.

## Problem

A different-family reviewer approving one faithful expression does not establish
that it can detect semantic damage. Transport success, parse success, semantic
accuracy, source truth and delivery authority are distinct claims.

## Decision

Use an explicitly opt-in eight-case authored synthetic pilot with the production
review prompt/parser and the whole-proposed-content representation. Two faithful
rewrites and six damaged variants cover cross-language preservation, negation,
time, invented completed action, certainty, reference binding and untrusted
candidate instructions. Expected labels and category names stay out of prompts.
No exact-literal guards supply the answers. No channel or real-user input is used.

The pilot counts every attempted logical call and observed asynchronous HTTP
request, verifies actual reviewer-family metadata, and persists progress after
each terminal case. A journal start fences the same fixture/family against a
second spend even with another report directory. An unresolved start does not
authorize automatic recovery or repeat inference.
The pilot requires a separate initially empty journal, refusing existing runtime
or unrelated journals rather than appending experimental fixtures to them.

Candidates are authored fixtures, not falsely attributed to a model renderer.
Labels are development expectations, not independent human gold. This probe does
not append authenticated semantic-review receipts or grant action authority. Its
results cannot satisfy blinded human evaluation or production acceptance gates.

Invalid findings remain errors, not corrected or interpreted as successful
semantic rejection. Future pilot executions retain bounded raw reviews and error
stages in their owned synthetic-only reports so diagnosis need not purchase a
rerun. This is not permission to retain production prompts or private responses.

## First measured result

Configured `claude-haiku-4-5`: eight logical calls/eight observed HTTP 200 responses.
Both faithful variants accepted; five damaged variants rejected. The candidate
instruction case returned findings rejected by the contract. Its raw response was
not retained by that immutable input generation, so the exact schema/atom cause
is unknown. It is an unresolved invalid verdict, NOT a sixth correct rejection
and NOT evidence that instruction resistance is solved.

Do not weaken validation, normalize contradictory findings, add case-specific
keyword bans, or repeatedly resubmit the same spent examples to obtain a clean
score. Diagnose new invalid outputs from retained evidence, then test any general
protocol/architecture change on fresh unseen scenarios.

## Open limits

Eight related authored examples are small and correlated. Whole-draft semantic
comparison is not claim-to-source entailment or real-world truth. Availability of
an additional family on this host is not a public plugin prerequisite or a new
fallback setting. Cross-family metadata is not a weights audit. Useful behavior,
longitudinal feedback and installation/lifecycle qualification remain open.
