# Hermes Alive Phase D / Interruption Policy V1 Contract

Marker: `INTERRUPTION_POLICY_V1`

Scope: dev container only.

Adds level 0-3 policy:

- level 0: silent
- level 1: ambient
- level 2: proactive
- level 3: emotional

The policy reads Alive State V1 and existing watcher signals. It must not send messages by itself and must not touch production.
