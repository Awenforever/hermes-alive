# ADR0212 — Explicit continuous native lifetime

2026-10-24 (Asia/Shanghai), Codex.
Status: implementation under isolated qualification; ordinary activation pending.

## Decision

Reuse AutonomousHostRuntime.run and NativeCognitionHost.start, not another
scheduler, daemon, queue or model router. The trusted execution host can request
continuous=True with no finite cycle budget and a strictly positive interval.
Without that explicit choice the existing finite 1..1000-cycle contract remains;
shadow hosts cannot request continuous execution. This flag is a lifetime choice,
not a route, model, retention or sending grant.

Each iteration still uses the existing durable operation identity, current policy,
native per-cycle model capability, exact send authorization and one-use outbox
start. Stop interrupts active work cooperatively and retains unresolved native
children through the existing reap path. A paused cycle exits the continuous loop;
a cycle failure exits without an implicit restart or provider retry. The owning
Gateway's task observation reports paused as stopped, not live readiness.
Authorization, consumed/unavailable attempts, reconciliation/content attention
and unexpected dispositions also exit instead of opening another spending cycle.
Only submitted, silence and waiting_for_change ordinarily continue. Attention
remains visible in task observation, not an invisible automatic restart.

The root Gateway attachment remains shadow-only until ordinary setup-to-execution
assembly is qualified. Do not widen it merely because continuous component tests
pass. A continuous loop does not establish durable agenda utility, delivery,
source quality, migration or conversational continuity.

## Required evidence

Check two distinct durable operations under one loop, fresh native capabilities
each turn, stop/pause/failure, rejection of implicit infinite budgets and zero-delay
continuous spinning. Separately exercise real standard executor submission across
a reopened journal: never resend the consumed first attempt, allow a distinct
authorized second intent, and stop new IO when policy is paused. Synthetic cadence
relaxation in that fixture is not a change to public or production defaults.

No normal adapter return becomes a delivery acknowledgment. No second physical
FIFO, foreign plugin dependency, Core patch or production mutation is introduced.
Consumer-installed ordinary execution, restart/compaction, exact older quotations,
full memory/permission migration, fleet and ten-round quality gates remain open.
