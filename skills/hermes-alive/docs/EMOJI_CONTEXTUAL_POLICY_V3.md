# Emoji Contextual Policy V3

Marker: `EMOJI_CONTEXTUAL_POLICY_V3`

Scope: `hermes-alive-v2-dev` only.

This aligns the base LLM system prompt with the already-updated style guard.

Rules:

- Emoji has no global numeric hard cap.
- Use emoji only when it fits the sentence, emotion and relationship context.
- Avoid repetitive or decorative stacking.
- Debug, audit, production-operation and serious contexts usually need fewer emoji, but emoji is not forbidden.
- Existing sanitization and style-guard code must preserve multiple appropriate emoji.
