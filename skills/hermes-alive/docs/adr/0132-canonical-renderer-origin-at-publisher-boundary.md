# ADR 0132 — Canonical renderer origin at the publisher boundary

Date: 2026-10-15

## Decision

The Alive publisher seam previously submitted generated text with transport
correlation only. Enhance therefore could label it `hermes` or use matching
foreground-turn evidence. Actual body provenance must come from the retained
model candidate, not the configured main model, reviewer, or chat-wide cache.

After fresh launch validation, the publisher resolves the canonical attempt's
authorization and its authenticated, current expression candidate. It checks
owner, selection and exact compiled body before passing `model_name` to the
adapter. Missing/stale/mismatched natural-expression provenance refuses sending;
it never guesses another model. A deterministic action without an expression
has no model attribution. No caller-supplied model override is added.

Enhance remains responsible for chunking and persisting the same model with
queued chunks. Alive neither edits that queue nor manufactures footer text.

## Evidence and limits

The composed real-journal/lease test checks immediate and deferred multi-chunk
submission using the actual development Enhance implementation. A deliberately
conflicting completed foreground model cannot override renderer provenance.
Every transmitted chunk retains `synthetic/renderer`; changed body attribution
is refused without journal writes. Linux uses the pinned native Hermes adapter
with synthetic physical IO and network/process IO forbidden. Windows uses the
fake physical adapter. These fixtures do not establish real-model correctness,
remote receipt, quote association, or production installation compatibility.

Initial tests exposed fixture assumptions: a tiny size minus footer reserve made
one-character chunks and exceeded a receipt page; larger fixed sizes did not
split the short body. The final fixture sizes from actual formatted body length
and footer reserve and asserts multiple host-defined chunks, without changing
runtime splitting or receipt pagination to make the test pass.

No production change, real send, model call, public release or enhancement final
acceptance follows. Continue useful multi-cycle real-model validation, novelty,
feedback/memory/agenda integration, lifecycle and migration/portable acceptance.
