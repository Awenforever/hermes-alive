# ADR 0261 — Distinct continued steps through the existing Core executor

Status: candidate implementation; bounded actual-Core controlled qualification, broader negative and real-model qualification pending.
Date: 2026-10-28.

An accepted ongoing item must not stop being useful just because its first Core
job ended. Conversely, deleting the first-work guard would turn unknown effects
into automatic retries. Build on ADR0260's owned evidence reader, preserve the
owner's automatic scope and Core's execution/approval ownership, and distinguish
remaining work from a replacement execution.

## Guided authority

The new setup choice `--confirm-core-work-continuation` records version 1 of
continued-work consent. It requires autonomous work and owned result review;
existing first-work-only grants stay unchanged. It does not require or imply
automatic agenda closure. Original requests, explicit amendments and historical
owner work instructions remain separate from interpreted task descriptions and
recorded results. Neither a model next step nor an old tool result grants tools.

## Admission and recovery

The existing owner wake may consider a subsequent step, using the same Core task
executor, scheduler, model configuration, project context and permission path.
Only owned perform-work records of that item/configuration are read. The current
candidate has explicit bounds: up to eight earlier work records, up to four
active-segment discovery pages per record and a shared 16384-character body
budget. It carries evidence coverage limits rather than claiming whole history.
Larger/incomplete discovery, unsettled, failed, unknown or owner-stopped work
blocks automatic progression. Historical owner-instruction bodies must be intact.

The planner must identify a distinct remaining step, preserve waits and later
limits, and refrain when the goal is already attained. Dependencies outside the
guided toolsets require the owner. Core completion is not goal completion, and
partial/active-segment evidence is not proof of absent earlier effects.

A continuation identity includes its actual preceding work and protected history
basis. The normal work lock and durable pre-dispatch intent remain. Revalidate
the current source before admission and the exact parent evidence before Core
activation and each later tool. A newly admitted different step or changed
history fences the old continuation. Do not rearm an uncertain job. The new job
retains its evidence prelude through Core and a separate final owner envelope;
bounded instruction inspection can read that envelope without copying the whole
prelude. Alive's structural journal stores references/digests, not evidence bodies.

## Qualification required

The first controlled journey requests two different file steps on separate wakes.
Actual Core tools must produce/read both files, leave the first file untouched
during the second step and submit exactly two jobs. Another wake must not invent
a third step. A separate cold process must recover both records and keys.
Automatic closure remains unselected. Preserve the legacy first-work-only tests.

Before this can count as qualified progression, also exercise owner waits,
outside-scope dependencies, amendments/revocation between decision and tools,
changing parent records, stopped/unknown/failed work, missing/erased bodies,
bounded evidence exhaustion, interrupted handoff and restart with pending work.
Then run actual inherited-model journeys and inspect original decisions/results.
Controlled provider compliance alone does not prove semantic judgment, universal
no-repeat behavior, full lineage recall, fleet compatibility or production safety.

The evidence-bounds and historical-instruction design may need revision after
these cases. They are current implementation limits, not a smaller definition
of the full continuous-assistant objective. No production deployment is authorized.

## Initial actual-Core qualification

r252 failed: preparation can be entered again after a job is submitted. The
candidate needlessly asked the planner about pending work, and the controlled
fixture caught it. Admission now observes pending/non-completed/stopped work
without replanning or retrying it. r253 also remains failed: the harness's generic
second cycle had already admitted the second step before a legacy one-job count
assertion. The dedicated continuation phase now owns those later cycles. Its
synthetic HTTP endpoint also reports unsupported request paths/key names rather
than raising an uninformative missing-messages error. These failures were not
retroactively changed to passes.

r254 passed ten actual-Core controlled cases, each with a separate cold process:
two distinct continued file steps, legacy first work, owner wait, cancellation,
reopening, before/after revision, partial/complete outcome and project work.
The two-step case submits two Core jobs, leaves the first file unchanged during
the second step, declines a third step and does not enable automatic closure.
The original process exited 0, with actual container die 0/destroy/absence and
unchanged official Core supplier. This is one controlled matrix, not ten fresh
natural sharing rounds or a real-model/production pass.

A strengthened r255 follow-up passed five actual-Core/cold cases. It changes the
actual parent Core definition after planning: the cycle returns evidence_changed,
does not create another job or second file, then restores the definition only as
a fixture to exercise normal progression. Additional direct assertions distinguish
revised historical work from cancelled/reopened lifetimes while preserving the
strict old-version tool fence; snooze/resume remains the same task life. The
original process exited 0 and the container actually died with 0, was destroyed
and was absent before logs were inspected. The Core supplier remained clean.

These two controlled matrices do not qualify interpretation of ambiguous owner
intent, real-model dependency decisions, pending-step restart, all retention/
erasure histories or a production lifetime. The pre-existing empty-automatic-
toolset inconsistency also remains: setup describes model-only work, while the
automatic source path currently excludes an empty selection. Resolve and qualify
that behavior before calling the guided scope contract complete.
