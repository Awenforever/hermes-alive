# ADR-0047: Task completion is not user benefit

Status: accepted for shadow factual evaluation

## Decision

Task completion/failure supplies a separate factual `task_completed` label.
It no longer votes on `useful`. Usefulness requires attributable explicit
user feedback; absent or conflicting feedback stays unknown. A task can
complete yet be unhelpful, or fail while still helping the user. Signed
transport/executor evidence cannot establish satisfaction by itself.

Strategy reports retain separate completed/failed/unknown task counts, in
addition to delivery status and user-feedback calibration. Operational success
alone produces no usefulness-labelled observations or usefulness Brier score.
Contradictory task observations remain unknown, not last-write-wins success.

## Downstream audit

Preference learning admits explicit feedback or an accepted reflection; it
does not directly promote task receipts to user preference. Reflection permits
repeated task outcomes as evidence for a reviewable hypothesis, but requires
user review before acceptance. This change does not ban operational learning:
execution reliability is useful evidence, just not a satisfaction proxy.

## Evidence and limits

Label/report tests cover task-only unknown usefulness, independent positive
and negative user votes, contradictory task results and separate report counts.
Outcome admission/replay regressions continue to pass. Evaluation, outcomes,
reflection and preference tests passed locally on Windows and in a disposable
NAS/Linux Docker container with no network and only a read-only source mount.
These are synthetic tests, not human calibration or actual channel qualification.

Remaining work includes duplicate-receipt treatment, deeper reflection scope
and cached-evidence validation, authenticating evaluator episode labels rather
than only their attempt metadata, and live longitudinal review. No production
deployment or user data rewrite is part of this decision.
