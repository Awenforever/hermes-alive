# ADR-0060: Model waits revalidate evidence and consent

Status: accepted for the unscheduled shadow kernel

## Context

A model response is not instantaneous. Other events can supersede its exploration
gate or selected intent while the operation waits. The user can also withdraw
learning consent or erase retained content. Checking only before the first call
can admit an outdated choice or disclose withdrawn excerpts in a plugin retry.

Execution reproductions demonstrated both failures: deliberation accepted a
response after a newer gate was projected; consolidation called the provider a
second time after learning consent had been withdrawn during the first call.
Existing sequential happy-path tests did not cover these temporal boundaries.

## Decision

Treat each model operation as an evidence/consent epoch, not an enduring grant.

- Deliberation re-reads the exact frame, owner, sensitivity, candidate content,
  latest gate identity/result and latest validated selection identity before
  every plugin-level call and after its response returns. Changed, unavailable
  or erased context terminates that operation without admitting its response.
- Consolidation binds the exact consent revision and retained evidence window.
  It rechecks both before each call and after return. Withdrawal/regrant of
  consent cannot revive a response under the old revision. Erasure, expiry or
  a changed evidence window requires a new operation, not a stale-prompt retry.
- A context invalidation is a distinct structural error, not a provider failure
  to retry. Other invalid-response retries remain bounded and must pass fresh
  context validation first. No raw prompt/response/error body enters receipts.
- A unique journal start is committed before the first provider call. SQLite's
  event-ID uniqueness admits only one caller for an operation ID. A crash or
  cancellation can leave an unresolved start; a later invocation with that ID
  refuses another call rather than inferring completion or spending twice.
  Existing result receipts also continue to fence older operations.

No configured provider/fallback changes are introduced. Hermes still owns
routing and its internal retry behavior. No callback here sends messages,
authorizes an action, executes tools or activates model memory proposals.

## Evidence and limits

Regression coverage includes a superseded gate, a superseded intent, erased
candidate/evidence content, consent withdrawal, a provider failure before a
stale-context retry, cancellation and simultaneous same-operation callers.
The original stable-context bounded retry and actual-response model attribution
checks remain. These are synthetic deterministic model callbacks, not quality
or availability evidence for real providers.

Revalidation does not make a model network request and database transaction
atomic. A request already in flight cannot be recalled; this boundary cannot
control retries hidden inside Hermes' provider implementation. Arbitrary
background-process/cache mutation, operator clock reconciliation and live
multi-profile gateway qualification remain separate gates. The send-time
authority/outbox checks are still required before any real external action.

This repairs temporal trust in existing cognition/memory stages. It does not
complete event-to-intent orchestration, human-calibrated semantic judgment,
longitudinal usefulness or production activation.
