# ADR 0154 — Scoped completion evidence before a production native caller

Date: 2026-10-16. Status: implemented opt-in evidence component; isolated Core proof.

## Problem and decision

ADR0153's diagnostic adapter knew the fake provider response directly. An actual
host adapter cannot call a configured route or the previous response's label the
current model. Use Hermes' existing pre_api_request, post_api_request and
api_request_error lifecycle observations instead of modifying Core or Enhance.

`alive_kernel.native_completion.NativeCompletionHub` is explicitly installed with
a host PluginContext. It has no default global instance, background listener or
automatic production registration. A concrete consumer is the opt-in actual-host
shadow probe: its fixture is discovered by the real PluginManager and forwards
real Core lifecycle events to this component. The consumer no longer reads the
physical-response test list to attribute the scoped result.

The host opens an opaque immutable scope with a random session/task pair and an
explicit owner. Only matching pairs are inspected; foreground and foreign scopes
are ignored before body access. Event identity is correlation within a trusted
host/plugin process, **not authentication against hostile in-process plugins**.
An observer instance must itself belong to an explicitly scoped host/profile.

Bounded request coordinates tie pre-request route, post-request response-model
label, provider, turn and exact normalized text hash together. No prompt, response
body, headers, credentials, reasoning or exception message is retained by the hub.
It stores only bounded identities, static failure classifications and text
length/hash. This is ephemeral method evidence, not a new unconsented event-history
store. Response-model labels are provider-reported, not proof of the physical model
behind an alias. Proxy headers and routing aliases remain distinct evidence kinds.

## Finalization and lifecycle

Finalization requires an exact completed native result: no failure, partial result,
interruption, response reuse or transformation; exact session/turn/route/provider;
one unambiguous successful completion; matching final text hash and length. Other
observed requests must be explicitly failed, not unfinished. Native API identity
counts are checked against the turn's api_calls; these are **not physical HTTP
attempt counts**, because SDK retry/fallback can occur inside one identity.

Identical completion re-delivery is harmless. Missing or conflicting pre/post
events, a missing response-model label, tool-bearing output, mixed final text,
unknown shape, ambiguous successful replies or budget exhaustion reject. A failed
finalization consumes the scope and cannot be reinterpreted as success. Scope
clones cannot finalize the original capability. No fallback attribution is guessed.

Open scopes and request/response sizes are bounded; cancelling a scope discards
its evidence and ignores late callbacks. Disposed registrations make completion
ineligible. Close retires all scopes and releases registration handles outside
the observer lock, attempting all disposals and reporting incomplete cleanup.
These actions **do not stop an agent, HTTP request, thread or subprocess** and do
not withdraw Enhance FIFO items. They grant no send, memory or learning authority.

## Evidence and correction from actual Core

Windows fake-event tests and a network-disabled/read-only Linux actual-Core probe
cover separate things:

- Fixtures exercise concurrent owners, foreground payload exclusion, exact/replayed
  events, failed-request then backup identity, missing labels/events, transformed/
  reused/mixed text, tool output, ambiguity, cancellation/late callbacks, bounds,
  scope clones, partial registration cleanup, disposal and retirement. These are
  mechanics, not real provider fallback qualification.
- Core discovers a temporary observer fixture through its actual PluginManager,
  with host-owned registration handles. AIAgent/SDK/turn facade/prompt assembly and
  native lifecycle dispatch are not replaced. Only physical HTTP is controlled,
  using synthetic replies and explicit metadata503. The hub identifies the
  completion-body model even when the native turn model is only the configured
  route and served_model is null.
- The canonical Alive memory/agenda/discovery/attributed-feedback shadow chain,
  zero-spend exact replay, then withdrawal/forgetting into a new native session
  still complete. The response-model label now comes from scoped post_api_request
  evidence, not a shared test-transport last-model variable.

The first actual integration failed because the fixture assumed an SDK message's
role attribute. The inspected Core passes `NormalizedResponse`, which has no role:
its assistant role is implicit in post_api_request. The hub now follows that actual
contract (an explicit non-assistant role still rejects), and the fake suite covers
this normalized shape. This was an adapter assumption, not a Core defect and not a
reason to patch production. Earlier failed source snapshots are preserved.

The corrected full-package Linux run completes all three markers:

```text
HERMES_ALIVE_NATIVE_CONSTRUCTOR_PROMPT_BOUNDARY_OK
HERMES_ALIVE_NATIVE_SHADOW_SOURCE_BOUNDARY_OK
HERMES_ALIVE_NATIVE_SCOPED_COMPLETION_OK
```

Each such complete run uses three synthetic provider replies, zero actual model
calls, zero sends and zero DNS/connect attempts. The current probe adds no
production hooks, configuration, model routing, permissions, queues or restarts.
The old unscoped probe mode remains an explicitly weaker diagnostic comparator.
The Core integration test requires actual Core and is not silently passed by the
small portable CI fakes. The pure scoped-event suite is included in portable CI.

An adjacent Windows regression independently fails in the old feedback-context
fixture: it asserts a candidate lives as long as its paired feedback, ignoring the
seven-day bundle cap added in ADR0147. The actual runtime already takes the minimum
of that cap, source expiry and feedback expiry. Do not lengthen retention to make
the fixture pass. Correct the expectation and exercise all three independently
winning bounds (long source/feedback, short source, short feedback), using an
explicit synthetic-feedback lifetime parameter whose original default stays29days.
This fixture repair is not a runtime policy change or proof of complete erasure.

## Next: process lifetime, not a cancellable-looking thread

This is not yet a production NativeAgentCaller. Existing outer Alive operation
records guard inference replay and revalidate current context after the await;
the scoped hub provides completion evidence, not replacement persistence.

Next connect it through an isolated, host-owned managed worker process. Simply
wrapping the synchronous native conversation in asyncio.to_thread and cancelling
the await is insufficient: a constructor or SDK request can keep running/spending.
The parent needs bounded start/IO, output/protocol limits, explicit cancellation,
terminate/kill plus authoritative wait, and cleanup only after the worker ends.
The child needs explicit owner/profile and model inheritance, no foreground session
or channels/tools, and no unconsented native memory/profile writes. Secrets must
not enter argv, logs, reports or public source. Unknown active-worker state must not
be restarted as a new model operation. Test these boundaries before real models.

Streaming, actual provider fallback, multiple-response native turns, transformations,
installed dependency/runtime admission, cross-device lifetime, full forgetting and
real-model usefulness remain unqualified. The full sustained memory/agenda/outcome/
reflection, external Halo, migration/rollback and production acceptance objective
is unchanged. Actual cumulative usage remains290 logical/304 observed async HTTP
starts; fake replies are excluded. No main release or production deployment occurs.
