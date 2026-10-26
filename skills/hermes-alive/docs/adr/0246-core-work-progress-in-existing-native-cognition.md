# ADR 0246 — Core work progress in the existing Native cognitive loop

Status: development implementation; isolated actual-Core qualification.
Date: 2026-10-26. Not production acceptance or semantic result verification.

Supersedes ADR0245's missing lifecycle-observation path only. Its authority,
retention, uncertainty and unresolved lifecycle requirements remain binding.

## Decision

Use the existing active, authorized owner cycle to read exact owned Core job and
execution identities. Record a protected `work.observed` event only when the
observed lifecycle facts change. Preserve request causation and do not ingest
Core output bodies, duplicate task text, create another timer, or submit jobs.
The current scan is bounded to 128 recent requests; it is not complete inventory.

The existing cognitive opportunity reader combines the original retained agenda
context with the current signed work observation. A stale Core definition or
execution state invalidates the snapshot until the next owner-cycle observation.
Replaced configuration or revoked background-work consent cannot consume an old
snapshot as current authority. Existing privacy, availability, retention and
agenda-state checks still gate the original content.

Both recipient-intent interpretation and downstream source excerpts preserve
lifecycle qualifications. These are already-delegated work opportunities, not
instructions to remind the user to do the work. The existing reconsideration
digest notices lifecycle changes; unchanged state can reuse verified silence.
Actual useful communication remains a model decision under existing contact and
Core/Enhance transport authority. Observation alone is not a notification promise.

## Truth boundary

`completed`, `failed`, `unknown`, missing jobs and definition drift describe Core
execution. They never establish independent task success, absence of partial
effects, agenda completion, retry authority or learned user preferences.
`automatic_result_followup_enabled` remains false: task-specific result checking
and autonomous follow-on work are still required. No hidden output-body parsing
or deterministic mapping of Core completion into a success announcement.

## Qualification and remaining work

The actual installed synthetic Core/Alive profile executes a Core Agent file-tool
job through a loopback-controlled provider. Before and after execution, the
assembled Native cognitive loop receives the real signed lifecycle facts and
abstains using a controlled caller. Unchanged status waits without inference;
completion reopens cognition while task success stays false and agenda active.
This is actual integration and state-change qualification, not real-model
judgment, useful contact, arbitrary task verification or production delivery.

Extend this same path with independent goal-appropriate evidence and accountable
later decisions. Do not add another general executor, output logger, scheduler,
model router or physical message queue. Corruption isolation, bounded inventory
pagination, uncertain-job reconciliation/cancellation, project context, original
request traceability, retention/lifecycle migration, real-model and fleet
qualification remain release gates. The useful-sharing gate remains 0/10.
