# ADR 0123 — Queue acceptance is not a physical send receipt

Date: 2026-10-14

## Evidence that changes the integration plan

Read only the production enhance source, not its private queue, chat history,
credentials or configuration. The exact exported `v021_bubble_footer.py` SHA-256
is `69201431728c990534594014526b67627028234c8bbbcac88857f15a197a7794`.
Its `send_text_chunk` returns None after enqueueing on a physical error or behind
an existing backlog. Its later `drain_pending` calls a captured original method,
bypassing the outer adapter method. Task inheritance cannot solve this bypass.

`run_host_enhanced_chunk_observation_probe.py` imports that exact externally
supplied module and patches a synthetic adapter. An expired-token-like fake
physical failure gives a successful adapter result and one outer normal return,
with one queued entry. A subsequent same-task drain succeeds physically, empties
the queue and does not produce another outer normal return. This establishes an
observation-contract mismatch, NOT a FIFO defect. The test has no real token or
network call and is not a live production send or an actual SDK-loop proof.

Windows and isolated Linux both reproduce it. Linux uses the retained current
snapshot plus explicit current-file overlays, network none, read-only sources,
bounded resources and an auto-removed container. Windows creates its event-loop
local wakeup socketpair before installing the test's network/process audit guard;
all module/test execution occurs after that guard. The initial audit-before-loop
attempt failed before exercising the queue and is not counted as evidence.

## Immediate correction

The direct observer refuses an adapter exposing the known active enhance pending
queue. The composed execution seam checks this before `begin_execution`, leaving
the lease/start unconsumed and calling no adapter method. The observer also checks
on entry so its standalone research API cannot accidentally qualify that seam.
There is no automatic fallback, method unwrapping, queue change or resend.

The existing operator qualification remains necessary for other implementations;
absence of this known marker is not proof that an arbitrary adapter has physical
ack semantics. This guard is NOT the final deferred-transport integration. Earlier
stock-adapter tests and chunk references remain local observations only and must
not be reinterpreted as production enhance acknowledgements.

The prepared-runtime tests verify zero `dispatch.started` events and zero adapter
calls on refusal, in addition to existing direct success/error/cancel/publication
failure behavior. The current-file Linux actual-stock-SDK regression also passes.

## Required integration contract, without owning FIFO

Use a host/enhance-owned receipt publisher, not a competing Alive queue:

1. A bounded opaque attempt/route binding must travel with the original submission
   and persist with each queue entry. Bind before enqueue; never infer ownership
   from body similarity, recency, chat alone, task identity or inherited context.
2. Distinguish submission acceptance, physical acknowledgement, terminal failure,
   expiry and ambiguous interruption. Queue acceptance is not `outcome.delivered`.
   A failed call after an earlier acknowledged chunk is not safe-to-retry evidence.
3. Publish at both immediate and deferred physical boundaries. One subscriber
   failure must not change send success, consume an extra queue item or resend.
   Handle replay and restart using stable transport-owned occurrence identities.
4. Alive's lease/start expires independently of a potentially day-long queue wait.
   Preserve the original attempt association without keeping a task/lease alive or
   authorizing a second submission. Acknowledgement after terminal local state
   needs explicit journal reconciliation, not bypass of current ownership checks.
5. Report coverage and finality explicitly. A client nonce is not automatically a
   server quote ID, a complete bubble inventory or proof that the user read it.
   Canonical quote feedback remains a separate independently qualified contract.
6. Keep publisher retention, shutdown and bounded async writer behavior explicit;
   redact private payloads. A silent lost callback cannot count as zero effects.

Any enhance change discovered necessary here is a separately scoped development
change. The user assigned its final release/acceptance cleanup AFTER Alive; no
production enhancement update, restart or release follows from this ADR.

Continue toward the complete autonomous loop, memory/agenda/model semantics,
longitudinal utility, controls, migration/rollback and production acceptance.
This gap reproduction and safe refusal are progress, not completion.
