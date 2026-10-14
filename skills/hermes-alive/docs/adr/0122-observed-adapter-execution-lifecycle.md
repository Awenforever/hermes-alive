# ADR 0122 — Prepared intent to observed adapter lifecycle

Date: 2026-10-14

## Implementation

Add `execute_observed_text_once` for an explicitly operator-qualified Weixin
adapter seam. It consumes one existing kernel lease/start, compiles exact
authorized text with the existing qualified profile/target/media preflight,
installs an attempt-bound observer, revalidates launch authority and awaits the
original adapter.send. The host adapter retains formatting, splitting, queue,
token and retry ownership. This is not a new platform sender or FIFO.

Finally closes the observer and attempts local trace publication. Normal SDK
result objects pass through unchanged, including false results. Original errors
and cancellation propagate after best-effort publication. Publication errors
never cause another send or replace a completed result; returned diagnostics
contain only the error class, not private/untrusted exception detail. Every
result still has external_delivery_proven=False.

SendPreparationRuntime exposes this adapter entry after its exact prepared-
attempt/lease checks, sharing those checks with the existing CLI entry. Both
remain explicit research/operator seams, not activated startup behavior. Other
platforms still require their own qualified observation contract; do not advertise
this Weixin-specific chunk prototype as universal channel receipt support.

## Evidence

Windows composed fake-IO lifecycle tests pass success, original exception,
original cancellation and observation-write failure. Normal object identity and
exact text are checked; one start is consumed and repeated execution is refused
without another adapter invocation. Closed local traces are written except in
the deliberately failed publication case. No delivery outcome is created.
Existing send-preparation regression also passes after the shared check refactor.

Linux current-file overlay runs the same preparation/planning/expression/grant
composition against the actual stock Weixin adapter.send with only chunk network
IO replaced. Success, SDK false failure, cancellation and publication failure
pass. The actual adapter may log the synthetic error as part of its unchanged
behavior; the observer adds no private error-detail logging. This does not prove
real network delivery, live plugin queues, new install or universal channel support.

Final hashes:

- execution seam: `43b3b2100e9d1019d901e5c70e1e0a8adbbd15ff505b81d2384f5da0b8a33a8f`
- prepared runtime: `499ff7cb612743e09eddef64be90c0a84e63791064ea3ade02696893ea37aebf`
- test: `650d1dd9a1b41636cce1541e5cdd723d2c5f4edf2df4486c57c69939a76b0a64`

The Linux process exits 0 with network none, resource limits, read-only source
overlays and disposable test labels/--rm. Container absence is checked; no retry
source tree remains. Production start time is unchanged. Zero real model calls,
private-chat reads, production writes or real channel sends occurred.

## Remaining

Publication currently runs synchronously through bounded SQLite ownership checks;
event-loop contention, asynchronous writer shutdown and late terminal transitions
must be qualified before gateway activation. Shared queued-worker task ownership
is explicitly unresolved, not guessed or fixed by reordering the queue. Next
integrate receipt production and canonical delivery/history/quote feedback,
authenticated controls/scheduling, real model semantics and longitudinal utility,
then portable install/migration/rollback and production acceptance. The full
Alive goal remains active and is not satisfied by these isolated contracts.
