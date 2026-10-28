# ADR 0272 — Private task execution and owner contact are separate scopes

Date: 2026-10-29. Status: candidate; full Native and real-task checks pending.

## Failure that must remain visible

In real synthetic run r327, recalled context reached the work planner. The Core
worker nevertheless rejected a fact embedded only in a model-proposed step.
Later cognition attempted an owner clarification despite the original task's
explicit prohibition on messages. The fixture's route check prevented sending;
that is a failed task, not a successful permission check. Factual, expressive
and usefulness reviews do not establish communication authority.

## Decision

Pass private advisory context separately to the actual Core worker, with its
typed provenance and the existing selected Core request retention. Preserve
owner constraints and conflicting evidence. Advice supplies neither instructions
nor execution authority. Do not pretend a keyword appearing in a refusal proves
the worker used the fact correctly.

New agenda creation exposes `notify_owner`, default false. The main agent
interprets the current owner's request under the existing intake grant: requested
reminders/reports can select true; private work or explicit no-contact selects
false. Do not ask for another per-item confirmation when the existing delegated
grant applies. An ambiguous request does not gain contact scope. Global contact
and transport authorization remain separately necessary. The owner's preview
includes this choice for literal-confirmation creation.

Delegated intake signs this choice in the existing source receipt. Replaying the
same turn and request with a different choice fails without creating another
item or renewing retention. A missing choice in an old delegated record means
false. Historical literal-confirmation reminders keep their existing explicitly
confirmed scope; new confirmation previews include the conservative choice.
Ordinary revisions preserve it and cannot silently widen it.

Keep the complete private task view for memory preparation and execution. Use a
separate communication view that excludes private-only commitments before any
communication model inference. This avoids letting a model re-anchor a forbidden
task to an unrelated public source. Opportunity recovery uses that same view;
the existing selection-source validation runs again at dispatch start and just
before adapter launch. Private work continues, but an absent/withdrawn/erased
contact source cannot validate a retained message. A signed choice does not
require retaining an original body if that separate retention was declined.

This creates no send queue, language-keyword prohibition list, new executor,
provider or model routing. Wechat Enhance still owns physical FIFO and tokens.
It does not cancel private work or silently discard its results.

## Qualification

The focused synthetic test checks private tasks remain in private reasoning,
are absent from communication input, cannot be proposed by an adversarial model,
and cannot widen their choice on replay. A requested reminder remains eligible;
erasing its original retained source invalidates an already retained proposal.
Native intake/management, task revisions, memory-informed Core execution, actual
send-boundary regression and the wider portable suite still need qualification.
No production, publication or ten-round sharing claim follows from these tests.

### Bounded qualification result

r330 (candidate329) passed actual unmodified Core controls: work/new memory grant,
old grant without external recall, bounded retrieval refinement, three native
reminder intake/management variants, and model-only work with zero enabled tools.
r333's extended focused test also covers no-body-retention contact consent and
a whole private-task autonomous cycle that must never request an outbound route.
Candidate329 and333 runtime bytes, types and modes are identical.

Real inherited-model run r332 completed on candidate329. The same original task
caused Core to recall the synthetic teaching aid, and the actual worker produced
two activity lines using amber counters. Human review of the complete retained
worker statement confirmed application, rather than a keyword in a refusal.
Three cognition wakes abstained; adapter sends were zero. Nine Native logical
calls reported custom:ustc/deepseek-flash; the worker's HTTP model hop was not
observed. Credentials were audited absent and the projection removed after the
original terminal, Docker die/destroy and CID absence, before reading bodies.

This is one bounded semantic task pass. Core still reports completed result
unverified and agenda not completed; the fixture does not establish general
autonomous outcome verification. The inherited console summary's `jobs:0` is a
stale no-work-template field: the work status/evidence explicitly identifies the
one actual Core job. Do not use that counter as job evidence. Broad portable
qualification, explicit contact-scope changes on existing tasks, and all wider
acceptance gates remain open.
