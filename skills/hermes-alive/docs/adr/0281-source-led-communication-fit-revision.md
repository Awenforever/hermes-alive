# ADR 0281 — Source-led revision for a global communication-fit conflict

Date: 2026-10-29. Status: development candidate; qualification pending.

## Problem

ADR0280 distinguishes supported facts from suitable communication. Its existing
corrector, however, intentionally preserves opening, structure and depth while
editing exact unsupported spans. That is useful for a local error but cannot be
assumed to repair a whole message that is wrong for its conversational situation.
Detecting a bad share, or abstaining from it, is not a successful quality round.

## Decision and boundary

Use the existing once-per-selected-intent correction slot. Only a current v2
final-discovery assessment with an explicit communication conflict and retained
source evidence is eligible for `source-led-fit-revision-v1`. Factual findings
may also need correction, but they are not new evidence. A merely uncertain fit,
a legacy assessment or protected-purpose notification does not select this method.
Actual owner, selection, source availability and review validity are still checked
by the existing correction-context and revalidation APIs; eligibility is not a
permission decision.

This invocation can reorganize opening, focus and depth using original sources,
recipient context and required meaning. It must not invent facts, preferences,
history or promises to satisfy a critique. Preserve attribution, exact required
literals and speech act. No compulsory opinion, hook, criticism or word quota.
The response is either one complete `text` or explicit `abstain: true`. An
abstention creates no new candidate and has a distinct diagnostic error class.
Required-meaning review and complete factual/fit review still follow the revision;
a second rejection cannot create another correction slot.

Local factual-only corrections keep the existing exact-span editor. Both use the
same model task, inherited Core main/fallback, invocation count and finite budget.
No extra reviewer, provider registry, background executor or transport queue.

## Persistence and recovery

Record the selected correction method in the existing runtime start before
inference. A retained start keeps its old method, including historical `None` and
local-edit starts. A new global method cannot silently replace a pending local
attempt. Retain its exact parsed response in the existing protected vault with
the candidate's original retention bound and a separate source-revision purpose.
Its completion receipt binds original/revised digests, review/context, selection,
actual model/provider and no delivery authority. Current recovery reconstructs
the complete revised text from that proof; local proofs retain their exact-edit
reconstruction. Unknown, missing, foreign or altered proof is not accepted.

## Qualification required

Test eligibility separately from authority, malformed output, explicit abstention,
required-literal loss and protected-purpose/legacy exclusion. Exercise an actual
encrypted discovery with an initially fact-supported global-fit conflict, one
whole-message revision, required-meaning review and a second complete assessment.
Keep model-call counts equal to the existing one-repair path. Cover a second
negative review, cold completed recovery without inference, altered receipts and
source erasure during revision with no send. The first desktop success case passes
these existing authoring/recovery assertions; the other cases remain pending.

Then force this path through the installed current Core SDK/registry/native chain,
followed by complete current regression and fresh actual-model conversation. A
controlled model supplying a good revised string is structural evidence only;
it does not prove autonomous quality, fleet or production acceptance.

## 2026-10-29 — Controlled qualification update

All four new integration cases pass: success with cold completed recovery and
altered-proof refusal, a second negative assessment, explicit abstention and
source erasure during revision. Existing local-correction, old v1 recovery and
dimension/boundary controls pass as well. In the success case the revised opening
and structure change, two complete assessments occur, model-call count matches
the existing one-repair path, and only the resulting quality witness can authorize.
No test actually sends a message.

The initial Core depth fixture had a wrongly indented assertion; its focused run
and first complete portable attempt stop at compilation and remain failures.
Correcting that test-only issue yields the actual current Core SDK/registry/native
stages reading, deepen, interpret, select, author, semantic, final, revision,
semantic, final. The fixture asserts exactly one corrected local adapter submission,
two final assessments, one revision, no pending work, 6000/15000-character untitled
reading windows and no actual model/physical send. A later fixture-only adjustment
makes the positive synthetic explanation agree with its positive fit enum; neither
fixture response is real semantic-quality evidence. Complete current regression,
actual-model quality, Git consumers, fleet and production remain open.
