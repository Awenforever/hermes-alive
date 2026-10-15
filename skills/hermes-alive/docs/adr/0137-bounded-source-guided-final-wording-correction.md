# ADR 0137 — One source-guided final-wording correction per selected intent

Date: 2026-10-15
Status: implementation under qualification; not deployed

## Why

Stopping unsupported wording protects a boundary, but permanently discarding a
useful supported intent because the renderer invented conversation history is not
the desired proactive behavior. Correct the wording without changing the selected
intent or bypassing review. This is not permission to rewrite a user-confirmed
body or to reinterpret the original draft as verified fact.

## Contract

After a current negative final-source review, the grounded preparation runtime
may open exactly one correction slot for that selection. Its identity depends on
the selection and phase, not the critique ID: another negative receipt cannot open
sibling generations. A review of a repaired expression cannot open a second depth.
The original expression and original review remain retained, not overwritten.

The renderer receives the canonical original meaning, protected links, actual
prior expression, verified review findings and original grounding snapshot.
Findings and prior wording are untrusted advisory inputs, not new facts,
instructions, consent, preferences or proof of prior delivery. The renderer is
asked to remove unsupported additions while preserving original meaning. A bad
original meaning cannot be made factual by inventing a replacement claim.

Correction input is reconstructed from current retained evidence, not supplied as
an arbitrary host string. The runtime binds its digest, review ID and ancestor to
the correction start. It rechecks across model awaits and on recovery. The new
wording gets its own fidelity review and exact-final-source review; authorization
binds the new expression and its positive witness, never the rejected old wording.
The final-source snapshot also binds and revalidates correction ancestry, so
erasing the original critique invalidates the new witness at core dispatch checks.

At most three additional logical calls are opened by this runtime: renderer,
fidelity reviewer and final-source reviewer. Each stage has existing call timeout
bounds. This is not a hard end-to-end cost/latency limit over provider retries.
Unfinished, failed and cancelled operations are not implicitly respent. A second
negative result or unavailable correction is explicit attention, not successful
silence or permission to send the rejected body. Cancellation propagates.

When an exact confirmation identifier is supplied, automatic correction does not
run; the result requires a fresh confirmation workflow. An original fidelity
rejection or protected-literal/renderer failure also still stops rather than
entering this source-guided correction path. These remain explicit future work,
not evidence that all expression failures now recover.

## Qualification scope

Synthetic fixtures inject an invented prior-conversation claim, then exercise
successful correction, repeated rejection, cancellation/reopen, critique erasure
during await, exact-confirmation refusal, alternate-critique sibling refusal,
positive-review refusal and late ancestry erasure at the core outbox boundary.
They assert call bounds and no actual adapter invocation. Their model judgments
are fixtures, not semantic truth or production utility evidence.

Initial full Windows/Linux repair fixtures passed before the final ancestry
extension. The latest code passes all five Linux repair modes, including sibling,
positive-review and late-ancestry-erasure refusal, plus all four Linux final
preparation modes. Windows passes the latest successful-repair case including
sibling and late-erasure checks; its existing preparation regression also passes.
Do not describe this as a full rerun of all five latest modes on Windows. Linux
uses an isolated read-only retained-module overlay with network disabled, not a
fresh installation. No new real model calls: cumulative counts remain 119 logical /
132 observed HTTP starts, zero sends. Production and public release are unchanged.

Next: finish latest regression qualification, then fresh model-driven semantic,
utility and abstention controls. Preserve the full long-term objective: pending
intent controls, attributable delivery/feedback, layered/external memory, sustained
agenda and reflection/learning, forgetting/privacy, authenticated host lifecycle,
portable installs/upgrades, migration/rollback and genuine production acceptance.

### 2026-10-15 — Latest Windows matrix and observable no-respend assertion

All five latest Windows modes now pass. The forbidden provider callback records
each invocation independently of raising an assertion, and the test requires an
empty record after reopen and sibling-repair refusal. This matters because the
bounded repair path intentionally catches provider exceptions; an assertion
alone could be caught and mistaken for proof that the callback was not called.
No runtime defect was reproduced, and no real-model, fresh-install or delivery
qualification is inferred. Real-model totals remain 119 logical / 132 observed
HTTP starts; no actual sends or production changes.
