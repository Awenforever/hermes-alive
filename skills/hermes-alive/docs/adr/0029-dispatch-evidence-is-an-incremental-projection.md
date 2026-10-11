# ADR-0029: Dispatch evidence is an incremental projection

Status: accepted for the shadow kernel

## Context

The crash-safe outbox originally found `dispatch.started` and terminal result
facts by scanning the complete journal in reverse every time `reconcile()` ran.
That preserved correctness in a small test history, but made acquisition cost
grow with the lifetime of the assistant. A permanent agent cannot treat all of
history as its polling queue.

A fixed look-back window would be faster but incorrect: a delayed terminal
receipt or a long-lived uncertain dispatch could fall outside the window and
be retried or remain unresolved.

## Decision

Maintain a disposable SQLite projection containing only authenticated dispatch
start/result event identity, type, sequence and attempt ID. Its checkpoint and
each batch of indexed facts commit in the same transaction.

Every derived row has its own installation-keyed authenticator and projection
metadata stores the expected row count. Outbox startup audits count, checkpoint
and row authenticators; a mismatch discards and rebuilds the projection before
it may support a lease decision.

Projection captures the journal's current sequence as a watermark, processes
bounded transaction batches, and continues until it reaches that watermark.
The batch size is a resource bound, never a correctness cap. Events appended
after the captured watermark are handled on the next run.

The journal remains the source of truth. Candidate evidence loaded from the
index is fetched again from the journal and its installation-keyed
authenticator, causal order, attempt, start generation and outcome are
revalidated. The index can be deleted and deterministically rebuilt from
sequence zero. Startup recovery reports its checkpoint movement and catches it
up before outbox reconciliation.

## Consequences

- Normal acquisition work is proportional to new events and evidence for the
  relevant attempt, not total lifetime history.
- Invalid or unauthenticated look-alike events advance the checkpoint but never
  enter the evidence index.
- A crash before a batch commit changes neither rows nor checkpoint; a crash
  after commit preserves both.
- Concurrent projectors serialize through checkpoint compare-and-advance and
  cannot duplicate evidence.
- Projection corruption is repaired by rebuild; no raw message or route
  content is copied into the derived table.
