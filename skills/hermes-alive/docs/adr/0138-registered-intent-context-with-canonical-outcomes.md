# ADR 0138 — Registered intent and canonical outcome context

Status: implemented in isolated development, qualification in progress.
Date: 2026-10-15.

## Problem and decision

Prior wording alone cannot distinguish an internal draft from a registered action.
Repeated autonomous cycles could therefore propose the same contribution without
knowing that an earlier action attempt exists. Adding an independent Alive FIFO
would violate the transport ownership boundary. Inferring queue membership,
delivery or failure from an attempt would instead manufacture facts.

`ActionHistoryReader` exposes a separate bounded view of registered communication
intent. It intersects retained authenticated wording with owner-scoped journal
attempts, authentic historical authorization, and the matching admitted projection
row. Historical receipt expiry does not erase registration, but registration must
have occurred inside the original permit interval. This is not a reusable permit.

Only canonical, attributed outcome rows with intact retained content contribute
named outcome facts. The existing outcome verifier checks their underlying
evidence and canonical occurrence; a cached row alone is insufficient. The reader
uses the same explicitly selected content vault as SendPreparationRuntime and
DispatchOutbox, not an unrelated default vault or an automatic filesystem search.
The first composed fixture exposed that vault mismatch; the failed result remains
part of the development evidence, not a model error.

## Boundaries

- The view scans at most 64 recent owner-scoped attempt records, intersects the
  existing bounded six-expression view, emits at most four entries and examines
  at most eight recent outcome rows per entry. This limits the view, not every
  possible internal cost of the existing canonical evidence verifier.
- No outcome body, raw route, account, Token or new preference is exposed. Wording
  is the existing bounded excerpt; repr excludes it. Scope/clearance precedes
  private content resolution. Erasure, missing content and failed integrity checks
  remove usable facts; database failures are not converted into successful emptiness.
- `registered_intent_only` means registration, not active queue membership,
  execution, a pending obligation, delivery or user receipt. Outcomes support only
  their named observed stage. Missing or truncated history never proves no effects,
  failure, permission to retry or a complete lifetime inventory.
- This is model decision context, not a semantic hard ban on future related
  contributions. Meaningful developments/corrections can remain useful. Actual
  duplicate-action admission and useful longitudinal decisions still need testing.
- No transport code or platform queue is changed. Enhance remains its independent
  owner and is now assigned to Qoder; Codex does not concurrently edit it.

## Integration and recovery

Opportunity interpretation includes `recent_action_history`, binds its digest,
and rechecks after model await and on reopen. Membership is anchored before the
interpretation start so its own later registered attempt cannot invalidate itself.
Outcomes of those earlier attempts are checked at current recovery time: a newly
observed result or erasure changes the context and invalidates the old completion.
Source-support review sees the same evidence stages and does not equate an
attempt with delivery. No new model-side authority is introduced.

Older research completions without this digest recover only when the new view is
empty; otherwise they require a new explicit operation rather than silently
inventing context. This is not a qualified production data migration.

## Evidence and remaining work

The composed synthetic fixture creates a real local authorization/attempt, checks
owner/clearance/sequence boundaries, forged-owner isolation and projection-row
mutation, feeds registration into the next interpretation, adds a synthetic
authenticated canonical delivery outcome and verifies stale-context refusal.
Outcome erasure and wording erasure remove the corresponding usable evidence.
Erasure during model await prevents completion; reopen preserves the current
view. Outcome facts include recording time and explicit newest-record-first order,
not an inferred current execution state. Latest Windows passes the fixture;
resource-limited network-disabled Linux passes it and the adjacent wording,
four final-preparation and five final-repair modes. No real channel send occurs.
The four entrypoints are registered in portable CI, but no full-pipeline pass is
claimed this turn, and no fresh-install claim follows from overlays.

Before this change, a separate real-model fault-injection probe made nine logical
calls/nine HTTP starts: supported control stayed unchanged; invented prior
conversation and completed-operation claims each received one correction and
fresh fidelity/source reviews. Reopen incurred zero provider calls. Initial
planning/wording/review were seeded, so this proves limited actual correction
behavior, not complete autonomous semantic quality, independence or ten clean
production cycles. The initial launch had a missing isolated profile environment
and failed before any model call; it was fixed, not counted as a successful case.

Next qualify new real-model longitudinal decisions using registration/results,
then unresolved-intent admission, attributable deferred delivery and genuine
feedback/learning. The full memory/agenda/adaptation, privacy, host lifecycle,
portable install, migration/rollback and production objective is unchanged.
