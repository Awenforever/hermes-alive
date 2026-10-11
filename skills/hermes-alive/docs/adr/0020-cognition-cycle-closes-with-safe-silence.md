# ADR-0020: The first integrated cognition cycle closes with safe silence

Status: accepted for the shadow kernel

## Context

The event journal, agenda, deliberation and exploration projections had strong
individual contracts but no single crash-safe operation proving they form one
coherent cognition cycle. Connecting them directly to the legacy sender would
make integration testing an external side effect and would grant an unfinished
selector more authority than its evidence supports.

## Decision

The first coordinator accepts typed action candidates produced by faculties and
persists this chain:

```text
candidate evidence + active agenda reference
  -> deterministic policy frame
  -> subject-scoped diversity annotations
  -> replayable exploration gate
  -> deterministic safe-silence selection
```

Cycle, frame, annotation, evaluation and selection IDs are deterministic and
semantic reuse is rejected. Every non-silence candidate has encrypted content
and diversity labels. Existing deliberation admission proves evidence subject
ownership and any agenda reference resolves to a live item for the same user.
The exploration gate can narrow but never widen base policy.

The coordinator always selects the injected silence candidate using the
structural identity `system/alive-safe-silence`. This is not a model
attribution. It calls no model, channel or tool and cannot create an action
attempt. A later selector must be a separate component with its own replay
quality gate; replacing safe silence is not an incidental coordinator option.

Every step is append-idempotent. Re-running the same cycle after a crash resumes
projection and returns the same durable result without adding events. Reusing a
cycle or content ID with different semantics fails closed.

## Consequences

- The kernel now has an end-to-end, recoverable planning path without gaining
  production authority.
- Integration bugs can be found before any message is composed or sent.
- A zero-candidate cycle is a valid, durable decision to remain silent.
- Model selection, action attempt creation, send-time context recheck and
  delivery remain explicit future gates.
- Faculty migration can target one stable candidate interface while preserving
  independent plugins and subject boundaries.
