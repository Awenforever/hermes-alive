# ADR 0069 — Revalidate the original evidence, not a moving discovery window

Status: accepted in the isolated kernel branch; production inactive.

## Reproduced defect

After one completed interpretation, ingesting one distinct new discovery made
`CognitionCycleCoordinator.prepare` reject the existing candidate before another
model call. Recovery compared its original input IDs with the current top-eight
discovery list. Additions or ranking-window changes therefore looked like source
withdrawal. Continuous discovery could prevent a still-valid intent from ever
reaching expression, or unnecessarily consume a new interpretation.

## Decision

Pin the authenticated observation IDs from the original interpretation start.
Resolve their current active agenda entries with subject, clearance, kind, state,
expiry and bounded identity filters applied before SQL LIMIT. Preserve original
input order and validate the same observation's current entity version, content
availability and provenance. The existing discovery API keeps its default ranked
window for new interpretation; pinning is an explicit bounded host request.

Use this pinned read both after interpretation's asynchronous model call and
when recovering a completed interpretation for selection/expression. The full
original discovery input remains the dependency set, including source items not
chosen by the model. Never narrow it to the selected candidate alone: comparison
or judgment may have depended on the other supplied input.

A new unrelated discovery does not change the old dependency set. Original
source supersession, expiry, unavailable/deleted content or inactive agenda still
invalidates it. Foreign-owner and insufficient-clearance reads return no private
evidence. Duplicate, empty, malformed or unbounded pinned identities are refused.
No source truth, fresh authority or delivery permission is inferred from survival.

## Scope and limits

User-context revalidation remains conservative and unchanged. New user preferences
can change the meaning/relevance of an old proposal, so this ADR does not declare
unseen memory/context changes irrelevant. A new source that semantically conflicts
with an old distinct entity is not automatically detected by identity pinning;
claim-to-source entailment and contextual reconsideration remain separate work.

The old intent remains eligible for fresh host policy and selection, not mandated
for sending. Timing, alternatives, interruptibility and user benefit still belong
to the current decision cycle. All changes are isolated; no production activation.
