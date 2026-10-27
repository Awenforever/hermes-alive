# ADR 0253 — Stop owned work through Core and report what actually stopped

Status: implementation candidate under isolated qualification.
Date: 2026-10-27.

Agenda cancellation does not stop an executing Core job. Add an explicit
`work_stop` main-agent operation under the existing current-turn owner/management
checks, and `/alive agenda stop-work <work-id>` for an admitted owner command.
These stop owned execution without completing or dismissing the agenda item.
Ambiguous language still requires clarification. Stopping reduces existing work
authority; it grants no new tool access and remains available while Alive is paused.

Verify signed work/binding ownership, current profile and exact authored Core job.
Under the existing work lock, persist a signed stop intent for the producer and
its existing inspection before Core IO. The existing pre-tool gate rejects new
tool calls for stopped owned work; no further inspection is scheduled. An already
in-flight tool may still finish. Disable/unload of that gate remains a separate
lifecycle qualification; this is not an OS sandbox or remote effect rollback.

Pause the existing Core schedule. For a known execution, call Core `cron.recover`
with its exact job/execution identity: this only observes, never submits work.
Verify the recovered authored job and use its owner-issued session/admission
receipt for `cron.cancel` and `cron.status`. Do not scan other sessions, invent
receipt IDs, execute a replacement job or introduce another scheduler/executor.
Run blocking control away from the Gateway event loop.

Distinguish schedule paused/no execution observed, cancellation acknowledged,
owner terminal observed, already-terminal execution and unknown outcome. None
proves earlier effects undone. Missing/changed bindings and unknown admissions
require reconciliation, not invented success. A terminal job must not be paused
or reactivated: r168 running-stop cancellation worked, but its repeat command
exposed Core's refusal to pause an already-ended job. Observe that terminal state
instead, including completion racing the pause.

One current owner request has at most one cancel dispatch. An unknown answer is
retained and never replayed by a wake or repeated model tool call. A new explicit
owner request may try cancellation again against the same Core admission. This
does not permit another work attempt. Literal admitted stop commands each carry
their own request nonce; Core cancellation remains idempotent.

Qualify actual pending and running Core jobs, no file effect after stopping,
failed cancellation transport with the real pre-tool fence, explicit retry of the
same admission, duplicate/foreign/stale authority and cold recovery with original
keys. Controlled provider tests are not real-model intent or broad lifecycle proof.
