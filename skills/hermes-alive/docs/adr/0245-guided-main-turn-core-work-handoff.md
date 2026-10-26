# ADR 0245 — Guided main-turn work handoff to native Core jobs

Status: implemented on the development branch; isolated integration qualification.
Date: 2026-10-26. No production acceptance or autonomous Native work-selection claim.

Supersedes only ADR0244's not-yet-implemented handoff status. Its Core lifecycle
counterexamples and separate-result requirements remain in force.

## Scope and authority

Extend the existing owner-scoped agenda tool with work/work_status. A clear
current owner request may hand a known, active, retained item and its exact version
to Hermes' own job system. This is an actual capability beyond reminders, but
the autonomous decision branch is still communication-only. Do not call this the
completed continuous-agent loop.

First guidance separately authorizes native Core work, its normal Core model and
profile context, and Core-owned task-record retention. Select automatic Core
toolsets; empty is model-only work. Earlier configurations stay off. Toolsets are
Core capability groups, not a directory or OS sandbox. Core's own disabled tools,
agent permissions and model/fallback resolution still apply. No model/provider,
recipient, script or project-directory override is accepted from the model.

Main-turn correlation reuses the actual Core dispatcher/session/turn ticket and
an exact current evidence span. These provide attribution, not independent proof
of the model's semantic interpretation. Item constraints and deadline reach Core's
prompt; source erasure, changed item/version, changed setup, stopped intake or
paused Alive authority block a new automatic handoff. Scope outside the guided
automatic set produces a temporary full preview and exact owner command; no job
exists before confirmation. Literal confirmation is recorded separately from
delegated interpretation. A new attempt on unresolved prior work also requires
review; unresolved/running operations cannot be silently replaced.

## Handoff and recovery

Use the existing journal/protector and one profile file lock, not a new executor,
daemon, provider router or physical message queue. Record the request and handoff
intent before calling Core create_job. Create a paused one-shot local-result job,
check its exact authored definition, bind its ID durably, recheck current owner,
item and grant, then record activation intent and invoke Core trigger_job.
Requested → handoff → bound → activation form a signed causal chain to the
original agenda proposal. Deadline, toolsets and source fingerprints are bound.
The task body remains in its existing agenda store and Core's own task record;
Alive does not create another body copy just to track the handoff.
Core's active scheduler provider registers the activated job; a partial registration
failure retains the exact existing job and an unconfirmed state, never a duplicate.

Replayed requests reuse one work identity. A crash after Core creates a job but
before Alive binds it stays uncertain; automatic replay creates no replacement.
The already-created paused job remains for explicit reconciliation. Query only
the exact owned job; detect authored-definition changes and missing records.
work_status can recover the association through an exact owned agenda item ID
after conversation reduction, without submitting another job or scanning private
task bodies into a prompt. Fresh-process reads preserve original keys and work IDs.

Core otherwise adds enabled MCP servers to nonempty per-job native tool lists.
Use Core's no_mcp sentinel to prevent that implicit expansion, while preserving
explicitly selected MCP toolsets; check Core's effective resolution before handoff.
An empty tool list stays empty. This applies even when another MCP server is
configured later. Do not silently expand the owner's automatic scope.

## Runtime truth and limits

Core completed/failed/unknown are execution facts, not semantic outcome receipts.
Keep task_success_proven=false and the original agenda active. Do not promise
automatic result checking or notification: that capability is not yet connected.
Results remain local; later useful contact must use Core/Enhance's channel path.
Handed-off items are excluded from ordinary reminders asking the user to do that
same work; their dedicated result/attention-followup path is still outstanding.
Pausing Alive stops new handoffs, not an already accepted Core task or physical
effect. Core task cancellation and Core record cleanup are separately owned;
uninstall/reinstall, grant replacement and migration still need lifecycle proofs.

Initial qualification used actual installed Core command/collector/dispatcher,
Alive's work bridge, native job store, an actual isolated Core Gateway/Agent and
the native file tool. A loopback test provider supplies controlled replies across
processes; no real model or channel is used. The exact assignment, file path and
constraint reach the worker request, and OS readback checks its real file write.
Outside-scope confirmation, repeated-call identity, prior-attempt disclosure,
definition-change detection, failure after actual paused-job creation and cold
association/key preservation are covered. The first test's parent-only HTTP
patch could not control Core's child Gateway; the revised test binds the real
isolated profile before Core imports and uses the loopback provider. Preserve
the original failed fixture evidence rather than calling it a functional pass.

Still required: actual main-model use of this interface, autonomous Native work
selection, independent task-specific verification and feedback changing later
decisions, safe resolution/cancellation of uncertain operations, project context,
complete original-source traceability, Core-context/noise boundaries, lifecycle,
four-platform distribution, migration/rollback and production qualification.
