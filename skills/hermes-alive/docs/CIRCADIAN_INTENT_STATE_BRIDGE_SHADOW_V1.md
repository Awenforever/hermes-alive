# Circadian Intent & State Bridge Shadow V1

This phase connects fresh user messages to the deterministic Circadian Engine without changing outbound delivery behaviour.

## Safety boundary

- Runs after `agent:end`, immediately after the local context queue refresh.
- Reads only the latest local user message.
- Uses deterministic patterns; no LLM is called for intent recognition.
- Applies only when Circadian is enabled and configured as `shadow`.
- Never sends a message, blocks a watcher tick, changes quiet-hours, changes interruption policy, or modifies footer metadata.
- A malformed or accidental `live` setting does not activate this bridge.

## Supported intent classes

Actionable Hermes-directed events:

- standalone goodnight or explicit request to sleep
- explicit request to stay awake / delay sleep
- explicit wake-up request

Non-actionable observations and queries:

- whether Hermes is asleep or awake
- the user saying they are going to sleep
- the user saying they are busy
- the user saying they will stay up late

User observations never mutate Hermes' sleep state in this phase.

## De-duplication and freshness

- Each user message is represented by a SHA-256 message key.
- The same message can apply at most one state event.
- Messages older than two hours are recorded as stale and never applied.
- Bridge state and JSONL observability contain no raw message body.

## State ownership

Actionable events are persisted only through `CircadianEngine.apply_event()` into the existing local circadian state. This affects shadow facts such as phase and planned sleep time, but it does not affect production delivery behaviour.
