# ADR0240 — Main-owned interpretation, owner-confirmed continuing items

Date: 2026-10-26. Status: development implementation, not production acceptance.

## Problem

ADR0239 restored source-free execution, but its agenda input was a synthetic
owner event. The actual installation had no conversational path from an ordinary
request to that agenda. A wake fingerprint is not a request, and allowing the
model to manufacture a USER_EXPLICIT event would merely hide this gap.

## Decision

Register `alive_agenda` through the existing Core tool registry only after
confirmed configuration attaches the current conversation continuity. The main
agent interprets natural language; Alive adds no intent regex or second model.
The tool can list a bounded view or propose a task with optional constraints and
timezone-explicit dates. It cannot select an owner, route, authority or action.

The existing Core main-turn collector supplies an exact current scope/task
ticket. Cron, delegated, foreign, stale and uncollected calls refuse. Proposals
remain bounded process memory (16 drafts, eligible for ten minutes); creating one stores no
chat-derived body in the journal/vault. Show the full preview, dates, retention
period and exact confirmation command. `/alive agenda preview <handle>` is an
independent exact preview; no heuristic chat-text interpretation is involved.

An admitted owner command `/alive agenda accept <handle>` checks the current
configuration and exact conversation/session again. It creates the genuine
owner source event and existing USER_EXPLICIT commitment. This confirms saving
the displayed item, not its external execution. The model proposal itself never
acquires owner authority. A reset/reload, expiry, changed setup or wrong route
cannot reuse the handle. `/alive agenda done <item>` and `cancel <item>` use the
same admitted owner path and existing agenda transitions; finished items cannot
be completed or canceled again.

Only confirmed task/constraint/dates are retained, using the configured retention
duration disclosed in the preview. This is item-specific consent, not inbound
chat collection or permanent interest learning. Dates outside that retention
window or without a timezone refuse. Missing established agenda storage is an
error, never permission to create replacement keys. Discovery and Enhance's
physical FIFO/token/retry responsibilities are unchanged.

## Evidence and limits

Frozen r113 passes the four actual-Core focused suites. The installed source-free
test now uses Core's collector and tool dispatcher, exact preview and actual
owner command instead of injecting a fabricated owner request. It proves no
persistence before confirmation, unknown-task/date/expired-handle rejection,
exact owner provenance, one controlled reminder, completion without repetition,
missing-storage refusal and source erasure. Interpretation and Native model
responses remain controlled; channel submission is an in-memory adapter.

An actual inherited-main-model probe is separate. Tool availability in current
Core can be deferred through tool discovery; its first fixture incorrectly
required eager schemas and used a nonexistent agent shutdown method. That failed
before any model response and is not a product qualification. Preserve it;
the corrected probe uses Core's own discovery and close lifecycle.

No natural-language auto-acceptance, automatic completion, snooze conversation,
full inventory pagination, non-communication action grant, longitudinal learning,
fleet acceptance or production readiness is claimed here. The list explicitly
reports its eight-item bound and does not claim a complete inventory. The
unfinished quoted-feedback WIP remains separate. This closes an admission path,
not the full continuous-agent objective.

## Actual main-model integration evidence

The corrected r113 discovery probe completes two real inherited DeepSeek main
turns (four provider requests). Core's deferred tool discovery reaches
`alive_agenda`; the requested item remains temporary until the actual owner
command, its stated constraint survives confirmation, and completion uses the
same command path. Explicit synthetic casual chat creates no additional item.
No Native host is enabled, no adapter send occurs and no memory provider is
initialized. This is two synthetic cases, not exhaustive intent understanding,
end-to-end real-model reminder judgment or a fresh sharing-quality round.

The container exited0 and the substantive report passed. The host wrapper then
exited127 on an extra CR-only line from Windows file writing. Retain that wrapper
failure; do not silently change it to0. Independent postcondition reconciliation
confirms the absent container, unchanged Core, six-file credential audit with no
match and removed projection. Fix future script serialization to LF rather than
rerunning successful model calls merely to obtain a green wrapper exit.
