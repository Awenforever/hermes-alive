# ADR 0136 — Final-wording support travels with the dispatch permit

Date: 2026-10-15

## Problem and decision

Reviewing a proposal does not review the later renderer's words. A renderer can
introduce an invented previous conversation or user preference after selection.
Also, a passing in-memory preparation result is not a durable enforcement point:
another caller can reopen an attempt or use the core outbox directly.

In the opt-in grounded runtime, review the exact retained final expression against
canonical source/context/history before authorizing an attempt. An unsupported or
uncertain result creates no attempt; a rejected fidelity review is also stopped.
An interrupted review is unresolved, never automatically rerun on reopen. This
version does not yet repair a rejected final expression: it reports attention.

The signed authorization payload now optionally carries a final-wording witness:
review event, interpretation operation and independence requirement. Authorization
creation and reopening verify it against the exact expression, owner and selection.
The core outbox revalidates the same witness at existing execution/launch checks,
not only through SendPreparationRuntime's convenience wrappers. Missing, erased,
foreign, stale or non-supporting evidence cannot launch that bound attempt.
Reusing the authorization operation without its witness is a semantic conflict.
Review evidence remains a constraint on otherwise valid authority, never a source
of user consent, delivery permission or factual truth.

The older ungrounded research operations remain explicitly identifiable. This
optional witness does not prove every arbitrary caller requests grounded behavior.
Public activation policy and legacy-data migration are still open, not silently
redefined by adding a passing fixture.

## Configured models, not public provider dependencies

Single-family installations can use an honestly labeled correlated fidelity and
source review. The default independent-review reader stays strict. Grounded mode
explicitly chooses correlated review unless the host requires independent review;
strict requirements remain bound on recovery and cannot be weakened by a witness.
No provider, family or user's model setting becomes a public default. Correlated
agreement can repeat a shared model error; it is not independent corroboration.

## Actual evidence and limitations

The previously completed real-model run was read in this turn: 9 logical calls /
9 observed HTTP starts, all DeepSeek, zero sends. A development scenario completes
planning, expression and final support, and creates an isolated attempt; a
correction scenario chooses silence before rendering. Both proposal reviews say
supported; no repair is exercised. The report explicitly marks semantic quality
unqualified. This is plumbing evidence, not blind utility, correct abstention or
ten clean end-to-end calls. Cumulative counts: 119 logical / 132 observed HTTP
starts. Its exact temporary credential snapshot was removed after terminal state
and absence was verified. No new real-model call this turn.

Synthetic tests exercise supported/unsupported/cancelled final review, no-spend
reopen, same-family labeling, witness substitution, dropping a bound witness,
erased review content, direct outbox refusal without the preparation wrapper,
and successful local execution start with a valid bound witness (no adapter IO).
Existing authorization, preparation and autonomous cycle regressions pass on
Windows. Final results and Linux harness details are recorded in the living plan.

Still required: bounded final-expression repair without changing confirmed text,
fresh semantic/utility controls, pending-intent deduplication, real host launch and
deferred delivery/withdrawal enforcement, attributed outcomes and feedback,
layered/external memory, sustained agenda/adaptation, privacy/forgetting,
portable lifecycle, migration/rollback and production acceptance. No release,
production activation or ten-clean-cycle claim follows from this ADR.
