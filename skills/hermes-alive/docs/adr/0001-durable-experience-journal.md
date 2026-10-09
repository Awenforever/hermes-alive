# ADR-0001: Begin with a durable local experience journal

- Status: accepted for Phase 1
- Date: 2026-10-09
- Revisit when: multi-device active/active execution or journal throughput makes
  the local design insufficient

## Context

Hermes Alive 2.9.8 persists useful state across several JSON and JSONL files,
but those files do not form one ordered, causal history. A restart can recover
individual snapshots without explaining which experience caused a decision or
whether a partially completed action may be repeated.

The new kernel needs a durable substrate before adding richer memory, planning
or learning. It must work on ordinary Windows, Linux, WSL and NAS/Docker
installations without requiring a new service.

## Decision

Use an append-only SQLite experience journal with:

- immutable typed event envelopes;
- globally unique event IDs;
- correlation and causation IDs;
- canonical JSON payloads and integrity hashes;
- idempotent append with conflict detection;
- monotonically advancing consumer checkpoints;
- WAL mode, foreign keys and transactional writes;
- schema and application version metadata.

The journal records facts about what happened. Derived memory, agenda and policy
state will be rebuildable projections, not hidden mutations of event history.

## Why not adopt Temporal or LangGraph immediately

Their durable execution ideas are valuable, but a mandatory service or broad
framework dependency would damage the plugin's portable installation contract.
The first workload is local, low-throughput and single-owner. SQLite gives us
transactional durability and replay while keeping migration options open.

If later evidence requires distributed ownership, the event envelope and
idempotency semantics can feed a durable workflow engine without redefining the
cognitive model.

## Consequences

Positive:

- one causal history for diagnostics, replay and learning;
- no network service or new credential;
- deterministic migrations and backup using standard tooling;
- a clean boundary between observations and projections.

Costs and risks:

- SQLite does not itself schedule durable workflows;
- application code must enforce one-writer/lease policy for long actions;
- sensitive data needs an ingestion policy before production mirroring;
- integrity hashes detect mutation but are not signatures against a malicious
  local administrator.

## Non-decisions

This ADR does not define memory retrieval, agenda scoring, reflection prompts,
or a replacement for the watcher. It only establishes the history substrate on
which those decisions can be evaluated.
