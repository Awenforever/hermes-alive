# ADR 0133 — Retained expression history for novelty deliberation

Date: 2026-10-15

## Gap and decision

Opportunity interpretation read user context and learned advice, but not previous
generated expression. New operation identities could make the same contribution
appear new to the model. Feed bounded prior wording into semantic deliberation;
do not replace novelty judgment with keyword gates or claim duplicate prevention.

The history reader filters owner in SQL, enforces clearance, validates the model
candidate authenticator and canonical candidate identity, and resolves protected
content with exact owner/purpose/sensitivity/digest checks. It retains at most six
480-character excerpts from at most 64 matching records. It does not re-run old
planning to grant historical wording current execution authority. Missing/erased
content is excluded; absence does not prove a topic was never discussed.

All entries say generated wording only, delivery unknown, not preference or action
authority. They may include unreviewed/non-selected alternatives; models must not
interpret these as sent messages or user enthusiasm. Meaningful corrections and
developments can justify follow-ups. This is not pending-intent reconciliation or
a hard ban on same-source discussion.

The model operation records only a digest of this input. Context changes during
the model wait refuse completion. Recovery reads the pre-start history snapshot
using a SQL before-sequence boundary, avoiding inclusion of the operation's own
later expression and avoiding unbounded historical recursive validation.
Erasure/change of the retained snapshot refuses stale recovery. This remains
bounded context, not a complete or tamper-proof lifetime history.

## Verification

Windows and isolated Linux synthetic tests use actual protected expression
evidence, check prompt inclusion/new-operation abstention, reopen recovery,
owner/clearance isolation, copied/changed evidence refusal and erasure. Windows
existing expression-runtime regression passes. Linux uses minimal overlays and
retained test dependencies with external IO forbidden, not fresh installation.
The synthetic caller chooses silence when history exists; this does NOT prove a
real model's semantic novelty judgment. Initial import-cycle and incorrect test
API assumptions were corrected before final tests.

## Next acceptance

Compare fresh-operation decisions on unchanged evidence, material developments,
corrections and independent interests with configured real models. Inspect useful
silence and follow-ups, not merely candidate counts. Then integrate trustworthy
pending/delivery/feedback history, avoid duplicate unresolved intent and bound
longitudinal cost. Preserve full agenda/memory/learning, migration/rollback,
portable onboarding and production acceptance requirements. No production
activation, message send, model call or public release in this change.
