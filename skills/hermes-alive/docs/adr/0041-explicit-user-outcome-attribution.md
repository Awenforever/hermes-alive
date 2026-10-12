# ADR-0041: User outcomes require explicit causal attribution

Status: accepted for new shadow outcome admission; legacy revalidation pending

## Finding

ADR-0008 originally checked source type, user, actor and journal order, but did
not bind an inbound observation to the cited attempt. Any later message from
the same user could be claimed as a reply or feedback. A linked ordinary reply
could also be labeled explicit feedback solely through model-provided details.
Those outcomes could contaminate reflection and learned preferences.

## Decision

New user outcomes require the source event's `causation_id` to name the exact
`action.attempted` event. Source observation time cannot predate the attempt;
the outcome event cannot predate its source. Existing subject, actor, source
type and sequence checks remain mandatory.

Ordinary attributed replies support `user_replied` only. Correction, dismissal
and explicit feedback additionally require the host's typed
`user_outcome_kind` metadata to match. This field represents an explicit user
operation, not inferred sentiment or a string parsed from arbitrary prose.
Models cannot upgrade a reply by inserting claims into outcome details.

The future host feedback bridge must resolve a user-selected/quoted message to
an exact attempt before publishing attributed inbound evidence. Missing or
ambiguous references stay unknown; never assume the most recent action.
Host event integrity and authorization remain prerequisites. Raw user text
must not populate reserved host metadata.

## Evidence and remaining safety work

Regression tests reject unrelated same-user messages and ordinary replies
misclassified as explicit feedback. Attributed replies and explicit feedback
continue to support outcome, reflection and preference-learning tests.
Silence remains absent from the outcome vocabulary.

This change hardens new admission only. Previously materialized outcome rows
and dependent learned/reflection projections require a separate read-time
revalidation/migration audit before live activation. Preserve the journal and
encrypted evidence; do not erase history merely because its old attribution
does not meet this contract. Generic transport/task outcome attribution and
the authenticated dispatch receipt path also require separate audit. No live
feedback ingress or production deployment is claimed here.

On 2026-10-12 outcome, reflection and preference-learning tests passed on
Windows and in a disposable production-image container with networking
disabled and only read-only test-source access. Production data was not
mounted; the gateway remained running with its original start timestamp.
