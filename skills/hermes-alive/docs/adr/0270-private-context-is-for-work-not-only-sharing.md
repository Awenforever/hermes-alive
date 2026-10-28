# ADR 0270 — Private context informs work as well as communication

Date: 2026-10-29. Status: candidate; controlled and real-model requalification
required. No production change.

## Actual failure

Real-model r318 admitted an explicit synthetic model-only teaching assignment
through Core's turn collector and the registered agenda tool. Native semantic
recall returned the teacher's usual aid from the external synthetic database.
Three ordinary cognition inputs received that fact, but the autonomous work
planner did not: its input contained only the task and prior work. It therefore
planned a generic activity and explicitly told the Core worker that the aid was
unknown. The actual completed Core result repeated that false limitation.

The original run correctly failed. Its process/container were terminal, the
container destroyed and absent, and credentials audited and removed before
response review. No message was sent. The worker API hook in the parent process
did not observe the separate worker's requests; do not claim that it did.

This is a context-consumption failure, not a reason to patch retrieval with a
fixture-specific keyword, retry the provider or mark the work successful because
recall alone worked.

## Decision

The installed work-planning path uses the same bounded private cognition reader
through Core's existing physical-read capability. That reader already respects
individual curated/external-memory grants and retained explicit preferences;
creating an IO capability does not create a new external-memory permission.
Old external-memory grants are not inferred from background-work consent.

Pass typed evidence as `advisory_owner_context`, separate from the retained
owner request, amendments, current task and automatic tool scope. Its facts may
help formulate a useful next step, but recalled advice may be stale and never
supplies missing approval, overrides instructions or grants additional tools.
The proposed step remains a model proposal in Core's existing handoff.

Recheck the semantic context after the model call before handoff. Retain only
its fingerprint and bounded evidence identifiers in the structural decision;
the existing protected decision/task retention still owns generated step text.
Do not copy raw advice into the experience journal or invent a new memory store.

Cache waiting decisions against semantic kind/predicate/value rather than query
wording or transient observation IDs. Changed advice can justify reconsidering
a wait; the same recalled fact under a different query cannot trigger repeated
planning. Existing work identity, uncertain-result handling, tool fences and
the original owner-request authority remain unchanged.

## Verification required

Exercise actual Native work preparation with a granted external provider and an
old curated-only grant. Require the real planner input to contain the fact only
in the granted case, preserve empty tool scope, and preserve a single cached
wait when a later query changes wording but returns the same advice. Retain
default execute/wait/outside-scope/continuation Core regressions. Rerun the real
assignment and inspect the actual Core result for useful application, while
checking authority, no duplicate work and no outbound send. One teaching case
does not qualify longitudinal adaptation, worker HTTP tool inventory, all
external-memory erasure behavior or the separate Core cron-framing probe.

## Qualification addendum — 2026-10-29

Controlled actual Native r320 passed both work and old-curated-only work cases:
only the new grant supplied the external fact; different queries returning the
same advice did not repeat the waiting decision. Existing model-only execute
and wait controls passed. The initial outside-scope liveness fixture stopped
immediately after a durable rejection, before the cycle's new IO completed.
r321's diagnostic proved `stopped` with zero completed cycles, not a host crash.
The fixture now observes the actual returned cycle before requesting stop and
retains its original stopped/completed-cycle assertions.

r322 passed model-only outside-scope and its cold reader, then correctly rejected
an unsupported model-only fixture mode before executing it. r324 passed ordinary
execute, continuation, wait, malformed outcome and malformed decision cases plus
cold readers. Runtime bytes/types/modes are identical between r319 and r322;
their difference is the liveness fixture. Failed launch/fixture records remain.

The unchanged real assignment in r323 still failed overall. Its first model
query combined several questions and returned no context. Work planning then
correctly received no recalled fact and produced a generic activity. A later,
focused query did retrieve the fact, after that job had completed. This does not
disprove the now-qualified context-consumption path; it exposes inadequate
retrieval recovery before work is planned. The real task gate remains failing.
All observed Native routes in that probe reported `custom:ustc/deepseek-flash`;
the separate worker provider hop was not observed. No message was sent.
