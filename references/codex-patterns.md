# Codex Delegation Patterns for Hermes Alive

Proven patterns for delegating Hermes Alive modifications to Codex.

## Pattern: Audit → Fix → Verify

Always structure delegations in three phases:

1. **Audit first**: ask Codex to trace all code paths, cross-references, and edge cases before touching anything
2. **Fix**: clear boundaries — exact files, exact change types, what NOT to touch
3. **Verify**: provide a runnable verification script

## Boundaries Template

Every delegation must specify:

```
## ABSOLUTE CONSTRAINTS
- ONLY modify: <exact paths>
- DO NOT touch: <excluded paths>
- DO NOT restart anything
- Only change: <allowed change types>
```

## Verification Script

Always include a self-contained verification script that:
- Imports all changed modules
- Exercises the changed code paths
- Asserts expected behavior
- Prints ✅/❌ for each check

The script must run without gateway or WeChat dependencies.

## Key Files

| File | Role |
|------|------|
| `/opt/data/hooks/hermes-alive/llm_message_composer.py` | Message composition (LLM prompt, sanitize, compose) |
| `/opt/data/hooks/hermes-alive/proactive_watcher.py` | Main loop, adapter discovery |
| `/opt/data/hooks/hermes-alive/voice_engine.py` | Personality Genome + social_urge engine |
| `/opt/data/hooks/hermes-alive/cooldown_manager.py` | Rate limiting + quiet hours |
| `/opt/data/hooks/hermes-alive/handler.py` | Hook entry point |
| `/opt/data/config.yaml` | Main config (auxiliary.proactive section) |
| `/opt/data/.env` | Environment variables (PROACTIVE_*) |

## Never Touch

- `/opt/hermes/` — production gateway source
- `/home/vive/Work/Hermes/.../hermes-alive/src/hermes_alive/` — project source (uses package imports)
- Docker container while running
