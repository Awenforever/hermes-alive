# Hermes Alive Phase C / Alive State V1 Contract

Marker: `ALIVE_STATE_ENGINE_V1`

Scope: dev container only.

## Persistent file

```text
/opt/data/hermes_alive_shared/state/alive_state.json
```

## Purpose

Add a lightweight persistent state engine so Hermes Alive has:
- ignored proactive count
- recent openers
- recent speech acts
- mood dimensions
- current flow classification
- focus lock for debug/ops work

## Inputs

Read-only inputs:
- `/opt/data/hermes_alive_shared/context_queue.json`
- `/opt/data/hermes_alive_shared/proactive_log.jsonl`
- `/opt/data/hermes_alive_shared/voice_state.json`

## Outputs

Persistent state:
- `/opt/data/hermes_alive_shared/state/alive_state.json`

## Safety

The engine does not send messages and does not touch production.
In Phase C, it is developed and tested only inside `hermes-alive-v2-dev`.
