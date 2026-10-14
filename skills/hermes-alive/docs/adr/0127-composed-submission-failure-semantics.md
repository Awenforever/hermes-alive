# ADR 0127 — Composed submission failure semantics

Date: 2026-10-14

## Evidence, not new delivery authority

The prepared planning/expression/delegation/authorization pipeline is exercised
through the actual enhance publisher and its unchanged FIFO. Four controlled
scenarios verify the new published-channel entry:

1. An original send error before physical IO propagates as the exact original
   exception object, and another invocation cannot consume the same start.
2. A controlled original caller cancellation raised after successful queue
   submission propagates as the exact cancellation object. The FIFO entry and
   scoped queued observations remain; no implicit drain, resend or outcome occurs.
3. Removing the observation table after successful physical IO makes publication
   fail. The original SDK result object is still returned, with only
   `OperationalError` recorded as publication diagnostics; another invocation
   does not send again. No private error detail is put in that result.
4. A user-owned autonomy pause between publisher binding and final launch
   validation prevents any adapter invocation. One consumed start is retained,
   not reopened; no outcome is manufactured from the empty observation page.

Windows uses fake physical IO. Linux runs actual stock Weixin constructor/send
with only physical IO replaced, current kernel/producer source overlays, network
none plus audit guard, read-only mounts, bounded resources and --rm. Both finish
with `HERMES_ALIVE_PUBLISHED_CHANNEL_FAILURES_OK`; Linux exits 0. Multiple native
chunks can queue in case 2; no single-bubble assumption is made. Zero real model
calls, real network sends or private-history reads occur. No production deploy,
restart, configuration change or enhance release occurred.

These are injected original errors/cancellation, not a complete OS/task-shutdown,
network-failure or writer-lifecycle qualification. They do not prove that every
possible SDK result means successful delivery. Reports still deny external
delivery, complete inventory and canonical quote proof.

## Consequence for the complete product

Caller interruption is not host-FIFO withdrawal. Already accepted messages may
still be sent by the host on a fresh token. Alive must not treat interruption or
an empty/missing publication as no effects and repeat an action.

A genuine later user pause/revocation must instead reconcile outstanding scoped
submissions through an authorized enhance-owned cancellation interface, serialized
with its physical-send lock. In-flight/already-acknowledged messages cannot be
promised recalled; missing historical bindings or ambiguous crash windows cannot
be guessed. No such interface or automatic withdrawal is claimed here, and Alive
must not directly edit/drop/reorder FIFO rows. This is the next execution-control
critical path before autonomous production activation, alongside bounded consumer/
writer lifetime, finality/feedback, real-model longitudinal usefulness and portable
migration/rollback. The full goal remains active.
