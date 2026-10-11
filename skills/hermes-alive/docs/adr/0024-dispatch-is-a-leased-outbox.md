# ADR-0024: Dispatch is a leased outbox, not an in-memory send

Status: accepted for the shadow kernel

## Context

An authorized action attempt still must cross a process and transport boundary.
Calling a channel directly after selection loses work on a crash; retrying an
unknown call can duplicate a message. A durable attempt alone is insufficient
because workers need exclusive, expiring ownership and a way to distinguish
"not sent" from "result observed but outcome projection not finished."

## Decision

Recorded attempts are reconciled into a SQLite outbox. The outbox contains only
structural IDs, capability, idempotency key, sensitivity, encrypted content
reference and deadlines. Candidate plaintext remains in the content vault and
is resolved only for the holder of a live lease with sufficient clearance.

Claims use `BEGIN IMMEDIATE`, a random in-memory token, a stored installation-
local token digest, a pseudonymous worker ID, a generation counter and a lease
of at most 30 seconds. Expired leases may be reclaimed; prior tokens immediately
lose read and mutation authority. A dispatch cannot outlive the authorization
receipt's `valid_until` time.

Terminal Hermes adapter results must be structural, installation-HMAC-
authenticated events bound to dispatch ID, attempt ID, capability and
idempotency key. An acknowledgement without such evidence is rejected. The
outbox then reconciles that observation into the ordinary evidence-backed
outcome projection.

Reconstruction searches authenticated terminal result events before restoring
a missing outbox row. If a result already exists, the row is restored directly
as `acknowledged`, never `pending`; the missing outcome is then rebuilt. This
closes the crash window between transport success, outbox acknowledgement and
outcome projection.

ADR-0026 refines this lifecycle by adding a durable `dispatch.started` boundary
and an `uncertain` state. A lease is retryable only before that boundary.

## Consequences

- Concurrent workers cannot claim the same dispatch generation.
- Worker IDs and raw lease tokens are not persisted.
- A crash before external-start evidence permits bounded retry. A crash after
  start but before a result becomes uncertain and cannot automatically redeliver.
- Backpressure that exceeds the authorization deadline expires the dispatch
  instead of sending stale intent.
- No Hermes channel/tool adapter is connected yet. This outbox proves lifecycle
  semantics only; live execution still requires a separately reviewed bridge.
