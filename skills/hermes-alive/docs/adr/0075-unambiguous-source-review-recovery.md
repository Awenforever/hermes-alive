# ADR 0075 — Review recovery requires an unambiguous terminal history

Status: shared shadow recovery contract repaired; admission/dispatch still incomplete.

## Reproduced gap

The source-review verifier checked the completed record, its start, source/context
snapshot and retained findings, but did not inspect the operation's failed marker.
A journal with both completed and failed terminal records therefore resolved as
a valid review. A recovery path must not select the convenient successful record
and ignore contradictory history, even when the retained findings themselves parse.

The new ambiguity regression was run using the committed `d18f535` verifier in
memory, with synthetic local fixtures and no provider calls. It failed at the
expected assertion: the conflicted receipt still resolved. The fixed verifier
passes that regression. Historical evidence is retained; no production journal
was inspected, rewritten or repaired by deleting a marker.

## Shared rule

Validate the canonical start/completed operation identity and require absence of
the same operation's failed marker before resolving its current snapshot/content.
An otherwise matching completion alias attached to another operation's start is
also unusable. A failed operation must not invalidate a separate valid operation.

The same lifecycle is inherited by whole-message and claim-accounting review.
Tests cover conflict refusal, canonical completion identity, unaffected valid
receipts, source deletion, owner isolation and the spent-operation fence. No model
call is repeated to work around contradictory history; no inference or authority
is restored by recovery. A future explicit recovery/adjudication action must retain
the old history rather than silently remove it or fabricate successful completion.

## Scope

This closes the terminal-history issue recorded in ADR 0074's plan entry. It does
not establish correct claim extraction, source entailment, real-world truth,
current user permission or a verified action outcome. The semantic mixed-unit issue
and original pragmatic-label dispute remain open. No production activation,
external send, published release or full installation/lifecycle acceptance follows.
