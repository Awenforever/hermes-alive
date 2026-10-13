# ADR 0081 — Personal feedback belongs to the actual owner principal

Status: implemented and locally regression-tested; authenticated real gateway
feedback ingress and longitudinal benefit remain unqualified.

## Reproduction

The outcome projection previously required a user observation's actor to match
the recorded outcome's actor, but neither had to equal the personal subject.
An inbound event with actor `user:other`, subject `user:test`, correctly linked
to that subject's action attempt and marked `explicit_feedback`, was accepted.
The actual regression failed with `outcome='recorded', reason='observed_outcome'`.
A model principal could exploit the same representation ambiguity.

## Decision

For USER_REPLIED, USER_CORRECTED, USER_DISMISSED and EXPLICIT_FEEDBACK, both
source and outcome actors must equal the attempt's personal owner subject.
Admission returns `user_outcome_owner_mismatch` for a matching foreign pair.
Immutable evidence revalidation applies the same boundary, so migrated cache
rows cannot bypass it. Non-user authenticated delivery/task evidence retains its
separate transport principal rules. Shared/group audience opinions must not be
silently reinterpreted as a personal owner's preference; they require a future
explicit audience and delegation design.

This equality check is necessary, not user authentication. A writer that can
forge the owner's actor string remains outside the proof supplied here. Real
host identity, authorized ingress, user intent, quoted delivery linkage and exact
feedback meaning still need qualification. Typed metadata alone does not prove
that a model's interpretation matches the user's meaning.

## Verification and recovery

- Outcome regression covers foreign human and model principals, injection of
  legacy cache rows, current reads and rebuild, and retained original journal.
- Preference regression injects a foreign feedback cache row and verifies that
  learning rejects its observation and leaves the owner's estimate unchanged.
  The positive control still accepts the owner's explicit feedback and applies
  the bounded 0.25 support weight.
- Local Python 3.14 outcome, preference learning, reflection and evaluation
  suites all pass. Delivery plus an ordinary reply still yields unknown useful
  benefit, not a positive label.
- No journal erasure or schema migration, keyword sentiment patch, new grant,
  production deployment or user message. This is not full feedback qualification.

The same four suites also pass in the NAS managed Python 3.13 environment with
network disabled and only the owned scratch tree mounted read-only. Input tree:
`191b2278c9a102e5a0b3ae20fe54d89f82a3dea8`; archive SHA256:
`97f1711f005e361ead59d1fc2e376cc815986c70d2ea9513b950c73e13302ae6`.
Container `alive-feedback-owner-offline-20261013-r1` exited 0, started
`2026-10-13T15:03:35.546848136Z`, finished
`2026-10-13T15:03:39.39709684Z`. Production was still running with original start
`2026-10-11T07:43:25.630569081Z`. This snapshot precedes only this evidence-note
addition, not a code change. Repository verifier passed in Git-index permission
mode; its materialized-mode warnings are not portable installation qualification.

## Continue toward useful cognition

Next: bind authenticated owner feedback to the actual delivered content and its
intended topic/presentation/timing target; distinguish explicit preference,
tentative semantic interpretation, ordinary engagement and observed task facts.
Exercise repeated decisions with unrelated, conflicting, revoked and erased
feedback, and evaluate user benefit independently from delivery success. Keep
natural expression quality, memory/agenda/adaptation, migration/forgetting,
portable lifecycle and production acceptance in the overall objective.
