# Phase D Interruption Policy V1.1 Hardening

Markers:

- `INTERRUPTION_POLICY_V1`
- `INTERRUPTION_POLICY_ENFORCEMENT_V1`
- `INTERRUPTION_POLICY_MSG_TYPE_V1`

Dev-container only.

Hardening guarantees:

1. Idle/casual modes may run discovery even before discovery availability is known.
2. `max_bubbles` is enforced in code.
3. `allow_emoji=false` is enforced in code.
4. Link bubbles are removed when content sharing is forbidden.
5. LLM fallback is policy-aware and Chinese.
6. Preferred speech act becomes the emitted message type.
