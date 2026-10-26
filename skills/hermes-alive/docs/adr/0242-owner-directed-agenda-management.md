# ADR 0242 — Owner-directed agenda management through the current Core turn

Status: implemented; isolated qualification, not production acceptance.
Date: 2026-10-26.

## Decision

The first guided choice may authorize both intake and explicit management of
ongoing items. Existing intake-only grants do not silently acquire management
authority. Keep the optional per-item confirmation path. Core's main agent
interprets the current owner's request; Alive verifies scope, current turn,
protected grant, exact evidence span and the current item version before writing
a purpose-bound signed transition. Do not impersonate literal owner confirmation.

Support completion, cancellation, snooze and resume. Completion is an owner report,
not an independently observed outcome. Cancellation affects only the Alive item,
not external jobs or already submitted messages. Snooze changes availability,
not deadline, description or delegated authority; re-snooze is a single transition.
Stale item versions require refresh. Repeated terminal operations do not recreate
items. Revoking intake retains already recorded items and their transition history.

Management visibility and execution eligibility are different queries. Future
snoozed items remain visible for management; default execution selection still
excludes them. Preserve expiry, ownership and sensitivity checks in both views.
Lists remain bounded and cannot prove a complete global inventory.

## Evidence and limitations

The first controlled integration failed because future snoozed items disappeared
from the management view. Separating visibility from eligibility fixes this while
retaining execution exclusion. The revised actual-Core scenario passes creation,
re-snooze, resume, completion, stale-version refusal and reconstruction after grant
revocation. Eight actual main turns preserve returned conversation history, reject
quoted completion, and perform owner-directed changes with inherited Hermes models.
Replies remain verbose; these are functional evidence, not natural-sharing rounds.

A separate two-process actual-Core test restores the same profile, SessionStore,
owner/configuration/activation and three identity/content keys. Startup restores
the active binding; the owned loop is stopped before model/action IO. The old
in-memory proposal expires, the durable item and constraints remain, and a fresh
Core turn completes it. The first test incorrectly called a model tool after an
intervening command without restoring Core session context; fix the fixture order,
not production authority checks. This is not autonomous post-restart decision,
daemon, real account migration, message delivery or four-platform proof.

Task/deadline revisions, independently observed noncommunication outcomes,
feedback adaptation, bounded original-source recall, rollback into older binaries
and full distribution/production acceptance remain open. Do not reclassify this
management implementation as the completed continuous-agent objective.
