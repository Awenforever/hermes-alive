# ADR 0244 — Core-owned work, separate result evidence and crash uncertainty

Status: architecture candidate; actual Core lifecycle verified in one isolated
nonmanaged Linux container topology. Alive action handoff is not implemented.
Date: 2026-10-26.

## Requirements and boundary

The owner chose automatic action scopes during first guidance and confirmation
for operations outside them. Intake, contact permission and passive observation
do not grant execution. Alive must decide useful ongoing work, carry reasons and
constraints, hand authorized work to Hermes, observe what happened, and revise its
agenda or behavior. Ten good sharing examples cannot replace that loop.

Use Hermes' existing job execution/approval facilities rather than building a
second agent, shell executor or scheduler. A toolset/workdir is not an OS sandbox.
Do not silently override Core's disabled tools, permissions, model/fallback chain,
profile boundary or existing memory policy. An absent usable Core capability is
a reason to ask or defer, not to invent a parent agent or bypass the tool guards.

## What actual execution disproved

Supported Core's public subagent lifecycle requires a live parent; process-local
handles cannot reconnect after restart. Core's scheduled jobs have a durable job
store, claim/execution ledger, script mode, agent mode and recovery. However, the
restart-safe external worker path depends on the real Linux/systemd supervision
topology. Ordinary container/CLI scheduling can run the orchestration in-process.
Do not manufacture supervisor markers to claim durable detached work.

The first probe wrongly expected an execution to become completed after abruptly
exiting an ordinary scheduler launcher. Its actual ledger remained running. The
corrected probe observes Core's documented recovery and independent effects:

| Case | Core execution ledger | Independent artifact observation |
|---|---|---|
| Normal script | completed | requested artifact exists |
| Script reports completion and exits zero | completed | requested artifact absent |
| Script writes, then raises | failed | partial modification exists |
| Launcher dies after script starts | unknown after Core recovery | script still produces its artifact |

Real Core create/pause/trigger/tick/execution/recovery APIs run in three separate
processes against one synthetic profile. No model or adapter is mocked into doing
the work; the test scripts are deliberately controlled workloads. A second tick
does not start another interrupted execution or repeat its append. This does not
prove every Core topology, arbitrary job idempotence, Windows supervision, host
reboot durability, natural intent, semantic verification or Alive action wiring.

## Integration direction

Keep the execution state and desired-result state distinct. A Core completed
receipt proves a completed run, not a fulfilled assignment; failed or unknown
does not prove that no side effect occurred. Do not map those labels directly to
task.completed/task.failed in the semantic outcome projection.

An Alive handoff must durably bind the exact owner, current authority and scope,
agenda/source revision, operation identity and Core job/execution identities.
Keep secrets and task bodies in protected existing stores. Treat job creation,
activation, physical execution and observation as separate crash boundaries;
resume observation of a known operation rather than create another one. Creation
with an uncertain handoff must not cause an automatic replacement job.

Prefer a paused prepared Core job followed by current grant/definition checks and
explicit activation. Local result delivery stays local: Alive may later decide
whether useful contact is warranted; Core/Enhance owns all physical channel IO.
Core retains its job claim, process supervision and worker lifecycle ownership.
Stopping new Alive initiative is not a claim that an existing Core job or its
script process has been cancelled. Cancellation requires its own actual result.

Observe task-appropriate evidence separately: artifact contents, API readback or
other current attributable results, not the same agent's assertion of success.
Retain unknown/partial results honestly. A desired result that exists after a
crash may settle the assignment without rerunning its side effect; an absent
result alone does not establish that a retry is safe. Outcomes/reflections remain
attributable and reversible, with authority unchanged by learning.

The next implementation must connect this through actual Alive decisions, owner
guidance/confirmation and Core execution, followed by independent result evidence
and a later changed decision. This ADR and the Core test do not satisfy that gate.
