# ADR-0290 — Continue after a settled Core model timeout

Status: implemented, controlled qualification in progress.

The real edge-VLM discovery trial obtained sources and three candidates.
The final review had no response and ended with `APITimeoutError`. There was
no admitted draft, adapter submission or ordinary continuation. The continuous
host ended with `cycle_failed`. That result would leave a live installation
idle after an ordinary provider interruption.

Classify a timeout only at the Core completion await, after the pending task
has settled and the model scope still verifies. Let Core own its existing
provider and fallback attempts. The host records a signed
`model_temporarily_unavailable` outcome and closes the current cycle. Its next
scheduled wake uses a fresh operation, current evidence and current owner
authority. The spent operation and any earlier job IDs stay in the journal.
The old read-only transport receipt cursor can be observed again. There is no
immediate extra provider request, renewed send permit or draft replay. Core's
existing fallback-health cooldown still applies to the next wake.

Other exceptions, unsettled work, revoked authority and unqualified model
responses follow their existing paths. A controlled test must establish the
timeout classification, a distinct subsequent wake, no dispatch and unchanged
failure handling. A new real trial is still needed for the quality streak.

A subsequent real transit trial reached the first reviewer. The reviewer
accepted source support and rejected a draft that had expanded into a full
service bulletin. A timeout on the corrected draft's second review was then
absorbed by the generic repair-error handler. The host received
`content_review_attention` rather than the model-timeout outcome. Typed Core
timeouts now propagate through both initial and corrected final reviews.
Other repair failures keep their prior classification. This run has no
submission, continuation or quality credit.

## Diagnostic deadline is a separate observation boundary

The real chart/document-VLM probe ended at its 1800-second whole-cycle
observation deadline. Several individual Core requests timed out; the
official fallback then completed two authoring stages. One factual/fit
review completed and rejected the first draft. The corrected draft's review
was still in flight when observation ended. The probe recorded no settled
kernel snapshot. An overall diagnostic TimeoutError therefore does not prove
a settled CoreModelTemporarilyUnavailable outcome or a failure of its next
scheduled wake.

Subsequent real probes must retain the exact review request before awaiting
its response. On their finite whole-cycle deadline they request pause and
allow a separate, bounded settling interval before attempting an offline
snapshot. A hard external termination still remains a failed observation,
never a successful pause, a recovered cycle or delivery evidence. This
changes diagnostic collection, not provider timeouts, the fallback ladder,
production model configuration or the product's existing stage allowance.

## A settled timeout must survive the cognitive stages

The later OCR regression read the official project post and then its README.
It completed its reading decisions, so the initial configured-route correction
was exercised with real sources. Opportunity synthesis subsequently received a
qualified `CoreModelTemporarilyUnavailable`. It recorded that class but wrapped
it in `OpportunitySynthesisError`. The host therefore reported `cycle_failed`
and stopped, instead of recording the model-unavailable outcome. This was a
product failure, unlike the earlier diagnostic deadline. It had no draft,
adapter submission or ordinary follow-up and earns no quality credit.

Required candidate synthesis, deliberation and semantic rendering/review now
retain their failed/rejected stage receipts and propagate that same typed Core
exception. Deliberation does not spend its own repair attempt on a settled
provider timeout. Initial/corrected source review already propagates it. Public
reading, private-memory question planning and the work-decision model paths
also preserve the exception. Optional feedback assimilation continues recording
an unresolved item according to its separate existing policy.

The classification is still narrow: the Core caller must have established
settlement and unchanged authority. Generic deadlines, uncertain physical work,
malformed model output, missing sources and revoked permissions keep their
existing handling. The change adds neither a provider retry nor a new send
permit. A new host wake receives a new operation and current evidence.

Qualification now crosses the full configured discovery path at reading,
follow-up, opportunity, selection, rendering, semantic review and final source
review. Each injected qualified timeout must close as model unavailable with
no immediate duplicate request, no pending work or send, followed by a distinct
normal wake. An installed Core journey separately exercises the Native wrapper
and original candidate-synthesis failure. Controlled responses qualify recovery,
not real-model usefulness or a sharing round.
