# ADR-0010: Learned preferences are bounded advisory estimates

- Status: accepted for kernel shadow development
- Date: 2026-10-10
- Depends on: ADR-0002, ADR-0008, ADR-0009

## Context

Explicit user preferences and statistical patterns are not the same authority.
Collapsing them into one profile lets repeated weak signals override a direct
instruction. Unbounded counters also create feedback loops: once the agent acts
on an estimate, its own choices determine what evidence it sees next.

## Decision

Explicit preferences remain `MemoryKind.PREFERENCE` records with user authority.
The learning layer stores only advisory binary estimates for a typed axis,
private key and option. Targets are encrypted; the structural projection uses a
keyed digest so topic names do not leak through the journal.

An observation must cite either an explicit-feedback outcome or a currently
accepted reflection. Model judgment alone, delivery success, ordinary replies
and missing replies are invalid sources. A single source can contribute only
once to one target. Per-source influence is capped, evidence expires, and total
support/opposition mass is bounded. The estimate therefore remains inside a
conservative interval and can never become an authoritative rule.

Retraction requires a later matching user inbound event. A retracted reflection
automatically stops contributing even if its observation record remains in the
audit history. Learned estimates are not consumed by live policy until held-out
replay demonstrates benefit without increased interruption or error.

## Consequences

- Repetition cannot overpower a direct preference.
- Estimates remain explainable as a set of independent sources.
- Private preference targets are erasable without exposing labels in history.
- Rollback is replay, not a compensating negative signal.
- The initial implementation is shadow-only and provider-neutral.
