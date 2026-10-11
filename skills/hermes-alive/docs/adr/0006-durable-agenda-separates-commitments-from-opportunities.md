# ADR-0006: Durable agenda separates commitments from opportunities

- Status: accepted for kernel shadow development
- Date: 2026-10-10
- Depends on: ADR-0001, ADR-0003, ADR-0004

## Context

Polling is not intention. A continuously useful agent must remember what was
promised, notice what may be worth doing, survive restarts, and explain why an
item still exists. Treating every interesting signal as a task would create an
interrupting, self-authorizing system. Treating every task as ordinary memory
would lose lifecycle, deadlines and completion evidence.

## Decision

The kernel owns a durable agenda with two explicitly different item kinds:

- a **commitment** is an obligation attributable to an authority;
- an **opportunity** is a possible future action, not an obligation.

User-explicit and migrated commitments may become active. A model or passive
observation may only propose a commitment for review. Opportunities may become
active internally because activation does not authorize delivery or any other
external side effect. External action remains subject to later deliberation and
policy gates.

Agenda descriptions are encrypted, erasable content-vault objects. Journal
events retain structural metadata, provenance and content references only.
Lifecycle changes are immutable events with a finite transition graph. Their
timestamps come from the journal event clock, so discard-and-rebuild is
deterministic. Authority-bearing transitions cite a durable source event;
user-explicit authority is accepted only from a matching inbound user event,
not from a caller-provided label alone.

Proposal admission applies the same rule, not only later transitions. Every
source event must belong to the agenda subject or be explicitly subject-neutral.
`USER_EXPLICIT` additionally requires the proposal actor and at least one
inbound authority event to be that exact subject. `SYSTEM_MIGRATION` requires a
system actor and an actual migration event. Existence of an arbitrary event is
never sufficient authority.

## Consequences

- A model cannot silently manufacture a promise on the user's behalf.
- Completion, dismissal, expiry and snoozing are distinguishable outcomes.
- An opportunity can disappear without implying that a commitment failed.
- Scheduling and deliberation can consume the same agenda without owning it.
- Policy and delivery remain outside the agenda projection.

The first implementation remains shadow-only. Later work must add operator
inspection/erasure, candidate generation, authority gates and outcome linking
before any production activation.
