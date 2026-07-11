# Hermes Alive Phase E / Interest Learning V1

Marker: `INTEREST_LEARNING_ENGINE_V1`

Scope: `hermes-alive-v2-dev` only.

Persistent files:

```text
/opt/data/hermes_alive_shared/preferences/interest_profile.json
/opt/data/hermes_alive_shared/preferences/feedback_log.jsonl
/opt/data/hermes_alive_shared/content_seen.jsonl
/opt/data/hermes_alive_shared/content_items.jsonl
```

Learning rules:

- Strong explicit positive feedback: substantial positive update.
- Strong explicit negative feedback: substantial negative update.
- Asking for a link or details: mild positive update.
- One unanswered proactive message: no negative update.
- Three or more repeated ignored messages: small negative update.
- All evidence is logged and bounded to reversible weights in `[-1, 1]`.
- No sensitive identity traits are inferred.
