# ADR-0013: Official hooks cross a structural privacy boundary first

Status: accepted for the shadow kernel

## Context

Current Hermes exposes `gateway:startup`, `session:start/end/reset`,
`agent:start/step/end` and `command:*`. The agent events include raw user text,
assistant responses, tool arguments and tool results. They do not expose a
stable inbound message ID, and an `agent:step` result is not itself a typed
success/failure receipt.

Copying those contexts into an append-only journal would defeat forgetting and
turn tool output into an accidental secret store. Ignoring them entirely would
leave Alive without a causal account of actual interaction.

## Decision

The first production-shaped adapter subscribes to all official lifecycle and
agent events, but admits only structural facts:

- installation-local HMAC pseudonyms for user, session, chat, message, model,
  provider and tool-name linkage;
- bounded presence/length buckets, iteration and tool count;
- explicit declarations that message, response, arguments and results were not
  stored;
- a persistent open-turn state that links start, step and end events;
- deterministic event identities for retry idempotency; and
- a durable `session.turn_interrupted` fact when gateway restart or a new turn
  supersedes an unfinished turn.

The stable subject is the pseudonymous user when Hermes supplies one, falling
back through conversation/chat/session identity. Session identity is the
correlation, not the long-term memory subject.

Raw content may enter only through a future explicit retention policy into the
erasable content vault. Tool success/failure may enter only from a native typed
receipt, not by parsing result strings.

## Consequences

- Shadow history can reconstruct turn topology without retaining conversation
  or tool content.
- Exact duplicate hook delivery is harmless, while legitimately repeated text
  after a completed turn remains a distinct experience.
- A crash is visible as interruption rather than silently clearing state.
- Semantic memory, task outcomes and content-level reflection remain disabled
  until consent, erasure controls and authoritative receipts exist.
