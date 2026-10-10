# ADR-0015: Tool outcomes require explicit core evidence

Status: accepted for the shadow kernel

## Decision

Alive observes tools through Hermes' native plugin `post_tool_call` hook rather
than recovering tool activity from assistant prose or the gateway's lossy
`agent:step` summary.

Every callback proves that a particular invocation reached a terminal observer
point. Alive stores only structural data: pseudonymous invocation coordinates,
tool name, bounded duration and the core-reported status/error type. Arguments,
results and error messages are never stored by this adapter.

Hermes currently computes ordinary `ok` and `error/tool_error` statuses by
examining the returned value. Those labels are not authoritative success or
failure evidence. Alive therefore records their outcome as `unknown` and makes
them ineligible for learning. It accepts only executor-authored terminal facts:

- `blocked`, `cancelled` and `timeout`;
- `error` paired with a non-`tool_error` exception/error type.

The observer is registered through the public plugin API, remains inactive
unless kernel shadow mode is explicitly enabled, and is idempotent when Hermes
supplies a stable tool-call coordinate.

## Consequences

- A completed callback is not confused with a successful real-world effect.
- Preference/reflection code cannot reward a normal `ok` label until Hermes
  exposes explicit status provenance or a domain supplies typed effect proof.
- Failure, cancellation and policy-block evidence can be learned from without
  persisting sensitive tool payloads.
- Missing invocation coordinates are retained as unlinked terminal facts, not
  falsely joined to a conversation turn.
- A future Hermes contract should expose `status_provenance` and, separately,
  typed effect disposition; Alive can widen learning eligibility only after
  that contract is observed and tested.
