# ADR 0141 — Real feedback preparation exposes a preflight gap and weak review

Status: partial real-model evidence and isolated runtime fix; not production.
Date: 2026-10-15.

## Evidence before claiming success

A three-case synthetic feedback run exercised actual opportunity interpretation,
grounded candidate review, selection, natural expression, final reviews and
authorization preparation as applicable. Prior delivery, user input and authority
were explicit synthetic fixtures. No adapter was invoked.

- Situational request to pause: the initial model still proposed a share despite
  seeing the recent meeting-related request. The next source/context review
  rejected that proposal, and one evidence-guided regeneration abstained. Final
  silence is useful failure containment, **not** an error-free initial decision.
- Courtesy acknowledgement: the model abstained rather than inventing a new
  interest or treating “thanks” as enthusiasm.
- Explicit correction: generation rejected the older scooter profile and chose
  the newer bicycle interest; selection and Chinese expression completed. The
  same-family fidelity/final reviews accepted it. Authorization nevertheless
  refused `route_binding_content_unavailable`: the synthetic host route was
  created in a different vault namespace from the explicit send runtime.

The ten logical calls/ten HTTP starts were not a fully executable positive loop.
The final wording also omitted the source's synthetic qualification; engineering
inspection retains that concern despite “supported” model markers. It has not
been independently adjudicated and is not fixed by a keyword patch.

## Additional diagnostic, preserved limitations

The suggested Qwen3.8 reviewer was absent from the current configured inventory,
so its export failed before any model call. An initial current-review setup also
failed before inference. Later metadata inspection showed the original candidate
was not expired, and an offline fresh synthetic copy could reopen interpretation,
expression and final snapshot. Do not label the earlier setup failure an expiry
or production migration defect without causal evidence.

A subsequent one-call historical review through a configured different-family
lane returned HTTP 403 / PermissionDeniedError. No independent review result was
obtained, no permanent model configuration changed and no same-family fallback
was counted as independence. The historical diagnostic never minted a live permit.

A selective rerun corrected the private fixture by registering a new synthetic
host route in the explicit runtime vault, and checked it before inference. The
candidate again followed the newer correction, but its source reviewer returned
`unsupported` with an empty unsupported-claims list and nonempty uncertainties.
The protocol correctly rejected this contradictory assessment. Planning stopped
as unresolved, **not** as successful silence, and no new attempt was authorized.
This two-call rerun remains failed; never normalize that verdict into approval.

Across this work: 13 new logical calls/13 observed HTTP starts, including the
failed different-family call. Cumulative actual totals: **145 logical / 158
observed HTTP starts**, zero actual sends. Model jobs are terminal; temporary
credential exports and owned model-test containers were removed. Production
start time was unchanged during each job. These are not ten clean cycles.

## Runtime change: structural route checks before model spend

The fixture error exposed a general cost/reliability gap: preparation validated
route-ID syntax before planning, but only resolved its host contract after model
work. A missing, foreign, revoked or unreadable route could waste all that work.

`SendPreparationRuntime.prepare` now validates authenticated binding metadata and
owner **before** private locator access, then checks the existing host execution
contract before invoking expression/planning. Failure is explicit and makes no
model call or permit. Internal/shadow cognition can still use the expression or
planning runtime; the send-preparation entrypoint requires a usable send contract.

This is not a platform-readiness/Context-Token probe, a new queue, a fallback
recipient or authority to send. Final authorization and outbox launch checks still
revalidate the route after model work. A route erased during the await cannot
benefit from an earlier preflight. No Core, Enhance, provider configuration or
platform FIFO is changed; Qoder's ownership remains intact.

## Qualification and next work

Windows and offline/resource-limited Linux pass missing-route, foreign-owner
pre-content-access, erased-route and post-preflight-erasure checks. Calls and
new interpretation-start records are independently counted: a thrown callback
exception alone is insufficient evidence of no spend. Linux also passes literal
feedback, explicit context, registered-intent, expression-history, four final
preparation and five final-correction modes. These are retained-module overlays,
not a fresh installation or complete CI run. The fixture is registered in CI.

Next implement/qualify one bounded source-review recovery that reconsiders the
original evidence when the review protocol itself is inconsistent. Preserve the
invalid original output and failed/interrupted history, never infer approval,
silently retry old jobs, or abort separately good proposals. Then rerun the
positive full chain and address the unsupported-qualification concern. Continue
useful temporal deferral, genuine tentative learning/reflection, full host and
privacy/lifecycle/production requirements; do not replace them with gate counts.
