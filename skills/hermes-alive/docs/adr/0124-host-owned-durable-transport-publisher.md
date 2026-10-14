# ADR 0124 — Host-owned durable submission/acknowledgement publisher

Date: 2026-10-14

## Development implementation, not activation

Enhance branch `feat/alive-transport-evidence`, commit `ff80ccb`, adds a producer
at the existing immediate/deferred physical-send boundaries. Alive does not gain
another Weixin FIFO, context-token owner or retry loop. The independent enhance
plugin has no dependency on Alive and its main/release/production remain unchanged.
The existing audit worktree was clean and matched the exact production module
hash from ADR-0123. It was reused; no new clone or full source snapshot was made.

An opaque 64-hex `_hermes_transport_binding_v1` correlation token is validated
before sending and scoped to the exact task/adapter/chat during submission.
It is not permission. A nullable queue column persists that token with each entry.
Old rows migrate with NULL and never acquire invented historical associations.

The enhance-owned SQLite ledger records `queued` in the existing enqueue
transaction and `acknowledged` only after the captured original physical chunk
method returns normally. Deferred acknowledgement and queue-row deletion share
the existing connection transaction. Stable occurrence/client references are
derived from binding/hashed account/chat/client identity; new records contain no
body, credentials, raw identifiers or exception detail. Distinct bindings in one
chat remain distinct after a later cross-task drain. Immediate unbound sends
avoid the optional telemetry write.

The adapter exposes `_hermes_transport_receipts_v1.read_receipts`, scoped by
account/chat/binding with bounded pagination. Repeated publication retains the
canonical record. Retention is explicitly seven days / 10,000 records. Reads
always deny complete inventory, external delivery and canonical quote mapping;
write health is only current-object availability, not historical coverage.

Metadata statement errors do not change a completed physical result or trigger a
retry. The tested missing-table failure still allows successful deferred removal,
so that metadata error does not leave an already-sent row for another drain.
Existing queue-removal errors retain the prior transport behavior; this does not
claim safety against arbitrary database/commit failures or power loss.

## Evidence and limits

Windows fake transport and Linux actual stock Weixin constructor/send with only
physical IO replaced pass: additive old-schema migration and repeated reopen,
two bindings sharing one FIFO, cross-task drain, route/account isolation,
pagination, idempotent replay, immediate acknowledgement, invalid metadata before
sender invocation, and immediate/deferred telemetry failure without resend.
Existing enhance bubble/model/context-token/FIFO/deferred retry tests also pass.

Final overlay hashes (local/NAS exact match):

- producer: `166a009be306c0fc7e30b47d1288093660690a44fa4df084d5b6c12cd88024ff`
- test: `8083ed719d194f094108c8e298cb18b3907d48bd28fb751dfc0368241bf34a71`

Linux exits 0, network none plus process/network audit guard, read-only sources,
bounded resources, --rm; no labelled test containers remain. Production start
time stays `2026-10-11T07:43:25.630569081Z`. The first Windows test failed during
temporary-directory cleanup because fixture SQLite connections were not closed
by their transaction context. Explicit closing fixed the test; that initial run
is not counted as a pass. Its synthetic temporary directory
`C:\Users\king_\AppData\Local\Temp\enhance-receipt-giwovkj7` is a cleanup follow-up:
the attempted exact-target cleanup was blocked by tool policy and not bypassed.
No private messages/models/network sends, production configuration changes or
production restarts occurred.

These overlays are not full-package fresh install/upgrade or concurrency/
performance qualification. A physical acknowledgement still is not user receipt
or server quote identity. Crash after external IO before journal commit is
ambiguous under the existing FIFO behavior. There is no publisher identity/
integrity qualification, submission-finality/expiry/interruption signal or Alive
ingestion yet. Do not remove ADR-0123's direct-observer guard or manufacture a
delivery outcome from these records.

## Next critical path

Bind the opaque token to a canonical Alive attempt/start and qualified publisher;
ingest scoped occurrence records durably/idempotently without consuming a second
send authorization. Represent missing/pruned/ambiguous evidence explicitly; late
acks must reconcile with terminal local state without reopening sending. Add
finality and authenticated quote feedback before preferences/reflection learn
from delivery. Continue useful autonomous scheduling and real-model longitudinal
qualification, then portable migration/rollback and production acceptance.
Enhance's independent final release/acceptance cleanup stays AFTER Alive.
