# ADR 0125 — Attempt-bound deferred publisher bridge

Date: 2026-10-14

## Implementation

`QualifiedReceiptPublisher` requires literal operator qualification, a source
digest matching the reader's actual source file, the adapter's own queue/publisher
instance, the exact profile and the expected profile-local database path. The
current contract is specifically enhance's publisher from ADR-0124 / `ff80ccb`,
not a universal receipt API. File qualification is not cryptographic proof of
SQLite contents or immunity to malicious code inside the same process.

`TransportPublisherBridge.bind` first revalidates the existing authenticated live
launch. It journals a signed binding for that exact start/attempt, route, account,
owner/sensitivity and publisher digest. An opaque keyed token is derived from
that binding. Replay is exact; it never grants a new send or leaks the raw route.

`ingest` verifies the canonical binding and publisher scope before reading one
bounded page. It validates phase, sequence, reference/occurrence shape, occurrence
derivation and reported timestamps before appending authenticated local reports.
Each occurrence gets a stable binding-scoped event ID. Exact replay returns the
canonical event; conflicting evidence refuses to overwrite history. Ingestion
uses the historical signed binding, not a still-live launch lease, and changes
neither dispatch state nor sending rights. Missing, pruned or empty pages always
retain uncertain coverage; no absence-of-effects inference follows.

`execute_published_text_once` qualifies source/profile before consuming a start,
compiles exact authorized text, binds the publisher and revalidates launch again
before delegating to the adapter once. It adds only the opaque binding/thread
metadata. Finally attempts observation ingestion; ordinary publication errors
retain only the error class and never retry or replace the SDK result. Original
send exceptions/cancellation are not converted into another send. The prepared
runtime exposes this entry after its existing exact prepared-attempt/lease check.
No automatic FIFO drain, background subscription, retry or production hook is
installed. The stock-only direct-observer refusal remains intact.

All new reports explicitly deny external delivery, complete inventory, canonical
quote targeting and delivery authority. They are local provenance of a bounded
host SQLite report, not a canonical transport result or a learning signal.

## Evidence

Windows fake transport: actual kernel discovery/selection/expression/authorization/
lease preparation followed by enhance's real queue/publisher code. Binding replay,
foreign lease/route/source/profile refusal, queue acceptance, reopen and late ACK
ingestion after lease expiry, event replay, changed reader refusal, conflicting
SQLite occurrence refusal, empty-page uncertainty, privacy and no delivery outcome
are checked. Existing prepared-runtime regression passes.

Linux explicitly overlaid current kernel files and the exact ADR-0124 producer,
using actual stock Weixin constructor/send with only physical IO replaced. The
first composed run failed because the test assumed one bubble: the real short-
chat splitter produced two. The corrected oracle independently derives expected
logical chunks from the actual host formatter/splitter, compares each exact sent
chunk without its enhance footer and compares all queued/ACK references in order.
No chunk merging or transport changes were made to get a pass. The subsequent
composed Linux process exits 0; Windows with the same multi-chunk-aware oracle also
passes. The initial failed Linux run is not counted as a pass.

Linux uses network none plus audit guard, read-only overlays, resource limits and
--rm. No full source tree copy, production send, real model call or private history
read occurred. Test-container absence and unchanged production StartedAt are
checked. These overlays are not fresh installed-package or production evidence.

## Outstanding before activation

The journal pages are not atomic across all records; bounded replay recovers
partial ingestion but cannot erase conflicting history. SQLite and source hashing
still execute synchronously; event-loop contention/writer lifecycle/performance
are unqualified. The producer lacks authenticated occurrence integrity, full
submission finality/expiry/interruption, canonical server quotes and complete
inventory. Wall-clock discontinuities currently refuse timestamp qualification.
The new send entry's failure/cancellation/publication-error composition needs
further adversarial tests, not inference from related earlier seams.

Next persist/reconcile consumer progress and lifetime without another send,
qualify ambiguity/finality and attributed feedback, then bounded autonomous
scheduling, real-model longitudinal usefulness and consent controls. Portable
installation/migration/rollback and production acceptance remain outstanding.
Enhance's final independent release/acceptance remains deferred until Alive.
