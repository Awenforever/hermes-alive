# ADR-0008: Outcomes require observed causal evidence

- Status: accepted for kernel shadow development
- Date: 2026-10-10
- Depends on: ADR-0001, ADR-0007

## Context

A selected action is not necessarily attempted, and an attempted action is not
necessarily delivered. User silence is especially ambiguous: it can mean busy,
satisfied, uninterested, unseen, or nothing at all. Learning directly from a
model selection, transport call, or missing reply would manufacture outcomes
and eventually distort behavior.

## Decision

The causal chain is explicit:

`validated selection → idempotent action attempt → observed outcome evidence`

An action attempt names the validated selection, selected candidate, executor
capability and an idempotency key. It does not execute the action. Adapters must
record the attempt around their own side effect boundary and publish a separate
receipt or observation event.

Outcome kinds are finite and factual: delivery succeeded/failed, user replied,
user corrected/dismissed, explicit feedback, and downstream task
completed/failed. Each outcome cites an existing source event whose type,
subject and actor class are compatible with the claimed outcome. Private detail
is encrypted in the erasable vault; the journal retains causal structure.

There is deliberately no `no_reply`, `ignored`, inferred sentiment or synthetic
reward outcome. Time passing may produce an `unknown` evaluation window for
metrics, but it never becomes negative evidence by itself.

## Consequences

- Transport success cannot be confused with user benefit.
- Retries converge through explicit idempotency keys.
- Feedback and corrections remain attributable to actual inbound user events.
- Learning code must consume observed outcomes, not infer them from absence.
- The kernel can audit failures without owning channel-specific execution.

The first implementation is shadow-only and records no production actions.
