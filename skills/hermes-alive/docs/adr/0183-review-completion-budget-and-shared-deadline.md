# ADR 0183: adequate review allowance without extra lifetime or partial admission

Date: 2026-10-19. Status: implemented; canonical qualification pending.

## Actual evidence

Two purpose reviews on different new materials request2500 completion tokens.
Both end first in length with visible text and then stop after Core continuation;
the combined result differs from the final exact native utterance. Rejecting it is
correct. These are unavailable reviews, not negative recipient judgments or JSON
schema failures. Final-request usage counters do not establish total reasoning use.

Two new original-context trials keep the exact task messages, Qwen model and180s
request lifetime, changing only the finite completion allowance to8192. Both return
admissible supported assessments with native completion evidence. Preserve them as
new diagnostics, not rewritten historical verdicts or fresh acceptance rounds.
They support a resource mismatch hypothesis, not universal latency/reliability claims.

## Decision

Use the existing8192-token worker ceiling for source-review completion, inherited
by purpose and final-wording source review. Some host model APIs charge reasoning
against completion allowance; no provider/model-specific override is introduced.
Strict output fields/size, exact native completion, independence requirements and
the one protocol-correction bound remain unchanged. Do not accept concatenated
partial text, reinterpret a suffix as the original response or retry a valid
negative assessment for approval. Models/auth/fallback remain host-owned.

Review also had an adjacent lifetime flaw: format correction received a new full
timeout, and direct cancellation could leave only a started event. New operations
record their completion allowance and shared-stage deadline policy. Initial call
and correction share the original timeout, with only remaining time passed to the
host caller and outer wait. There is no extra10s inference allowance or renewed
correction lifetime. Cancellation/interrupt records a failed terminal event and
re-raises the original exception. Host worker cleanup remains its own responsibility;
an arbitrary uncooperative callable is not claimed physically cancellable.

Completed old reviews keep their snapshot/prompt semantics; no historical content,
negative verdict, missing terminal event or spent operation is rewritten or rerun.

## Controlled qualification and product limits

Tests assert the larger finite allowance on both calls and inherited reviewer
types, remaining-time limits, rejection of incomplete native results without
format retry, negative/uncertain outcomes, independent-model checks, erasure,
cancelled terminal records and no-respend replay. Deterministic clock exhaustion
proves correction cannot start after the shared deadline; an in-flight timeout
also fails rather than becoming silence. The first new timeout fixture lacked
TimeoutError in its expected exception tuple; retain that failure and correct
the fixture, not production error semantics.

The first canonical run stops on an older composed-runtime assertion that every
review receives the full original timeout. Update source-review expectations to
positive remaining time bounded by the original cap, retaining exact checks for
unchanged rendering/comparison stages. Preserve that failed artifact and requalify;
do not restore per-attempt full deadlines to make the fixture pass.

Adjacent suites and a read-only retained full-chain replay qualify mechanics.
One full changed-task diagnostic on the prior public pool is pending at writing;
it is not new-source acceptance and cannot on its own prove recommendation value.
The actual article relations, tone, selection and meaningful qualifications still
need inspection. Independent model agreement is not ground truth.

Continue the bounded useful loop and full long-term memory/agenda/outcome/feedback,
host embedding/read leases, migration and ten fresh complete clean-round objective.
No production/Core/model configuration, other-plugin or wmw change, restart or send.
