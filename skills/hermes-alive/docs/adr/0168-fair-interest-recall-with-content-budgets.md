# ADR0168 — Retire collector-priority admission as a recipient-interest gate

Date: 2026-10-18. Status: implemented, qualification in progress, not deployed.

## Observed problem

Actual isolated code admitted nine authenticated observations plus explicit
interest memory, but supplied only the eight higher collector-priority entries
to the model. The desired low-priority resource was invisible. Better final
wording, a stronger model or repeatedly reading the profile cannot recover an
observation never presented. Increasing eight to another permanent priority cap
alone would reproduce the same failure at a larger count.

## Decision

Use the existing model judgment to jointly assess relevance and propose at most
four contributions. Do not add a competing model registry, keyword-interest gate,
vector service or another model call per cycle. Build a fair, bounded source
window first and supply explicit/learned owner context to that judgment.

For discovery observations, an optional owner-scoped agenda read rotates by
immutable source-event sequence before the database LIMIT, not by collector
priority. It wraps after the last presented observation. The admission reader
still authenticates current evidence and checks sensitivity, owner and expiry.
Current user commitments retain their due-order reader and are interleaved with
discovery; they are not reclassified as external news or send authorization.

The cognitive pass draws at most 32 current entries and admits complete existing
source representations within a 24,000-character context budget. It never trims
additional source qualifications merely to fill the window, never silently drops
the user profile to fit more articles, and fails when context leaves no usable
source budget. Existing summary excerpt bounds/visible truncation flags remain.
At most four candidates/eight explicit abstentions/eight reconsiderations are
requested. Everything else stays unassessed, not disliked, approved or delivered.

A completed interpretation records its original/next source cursor, pool/window
size and budget, explicitly world_coverage_proven=False. Retained load verifies
the same scan in start/completion and binds the next cursor to the last presented
owned discovery event. Missing/tampered provenance fails; failed/cancelled model
operations do not advance the cursor. This cursor tracks source presentation,
not semantic approval, delivery, a negative preference or a platform queue.
Explicit preference changes reset advisory scan position to reconsider older
material. Recent task facts alone do not reset it. Typed explicit preferences
are retrieved before situational facts in the bounded cognition context so a
burst of task facts cannot evict the profile merely through recency. Original
authority/source checks remain; this is not noise-resistant extraction of every
chat or a guarantee that arbitrary numbers of preferences fit the context.

Corrective interpretation pins the original primary sources of the reviewed
candidates rather than advancing into unrelated material or reloading every
unrelated entry in the scan. Its separate 32,000-character context budget leaves
room for the critique; it cannot silently expand to new source identities.
Source/purpose review and expression
recovery resolve up to the same 32 pinned observations. Reconsideration peeks the
next fair source window so silence over one subset cannot justify sleeping
through a different unexamined subset.

## Evidence and limits

Offline actual-kernel tests cover the nine-entry counterexample, foreign-owner
exclusion, full coverage over 43 short observations across two reopened passes,
long qualified excerpts under the content budget across six passes, unchanged
source qualifications, retained nine-source review/recovery, cursor tampering,
and no cursor progress on provider failure. Model responses in these tests are
synthetic: they prove admission and traceability, not model taste or usefulness.
Commitment cognition and both existing reconsideration tests also pass.

Native r5 uses nine operator-checked public reference pages, with the relevant
bicycle directory inserted last and given the lowest collector hint. One actual
Qwen3.8/custom:ustc call sees all nine and proposes the matching resource; reopening
needs no inference, no protocol correction occurs, and no action/authorization/
dispatch/send is created. This supports relevance admission, not full-chain quality.
The legacy draft again has an ambiguous verification-attribution phrase ('just
the directory structure'); retain that concern for recipient-plan/independent
final review, not a keyword deletion patch or a zero-error label. No production
deployment follows from this probe.

This does not perform personalized internet searches. It improves model access
to already ingested material without leaking private profile terms into external
search requests. Per-pass visibility is bounded; it is not proof of exhaustive
world coverage or complete processing of arbitrary corrupted/stale inventories.
The agenda scan itself is bounded to 1000 rows; adversarial inventories dominated
by invalid/superseded records need explicit stress qualification. Commitment
backlogs still have their separate due-order bounds. These limitations must not
be hidden behind a clean small-case score or a production-readiness claim.

Fresh public-material/native-model selection, broader regression, source access,
noise-resistant memory and the complete delivery/feedback loop remain required.
