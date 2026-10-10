# ADR-0017: Startup recovery is ordered and side-effect-free

Status: accepted for the shadow kernel

## Context

The journal and each derived projection are durable, but an event append and
its projection update cannot be one transaction across every subsystem. A
gateway may therefore stop after recording consent, a proposal, a review or an
outcome and before the corresponding projection advances. Waiting for an
unrelated later command to touch that projection leaves restart behavior
temporarily inconsistent.

## Decision

Gateway startup runs one cross-process-locked recovery supervisor when, and
only when, an existing kernel database is present. It first resumes durable
content erasure and retention expiry, then catches projections up to a stable
journal sequence in dependency order:

```text
retention -> consolidation consent -> memory -> agenda -> deliberation
          -> outcomes -> reflection -> preference learning -> exploration
```

Each projector retains its own monotonic checkpoint and idempotent decision
records. Recovery calls the public `project_new` contract in bounded batches
and fails if a checkpoint makes no progress. A later retry resumes from the
last durable checkpoint; it never rewinds already committed projections.

Recovery may update only Alive-owned local projections, tombstones and managed
encrypted content. It does not call a model, send a message, execute a tool,
change user consent or start an opportunity. Failure is logged but cannot stop
the legacy production watcher from starting while the new kernel remains in
shadow.

## Consequences

- The journal remains the source of truth across crashes and restarts.
- Pending erasure and accepted/rejected memory reviews converge without a user
  repeating the command.
- Multiple startup attempts serialize on an Alive-owned file lock.
- A fresh install with no kernel database remains untouched; recovery does not
  create an empty shadow store merely because the hook loaded.
- Future projectors must declare their dependency position and supply an
  idempotent bounded `project_new` method before joining recovery.
