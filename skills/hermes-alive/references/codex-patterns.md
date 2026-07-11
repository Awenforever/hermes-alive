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

## Audit Boundary Rules (防叠甲)

When delegating a final audit to Codex, include these hard constraints to prevent
infinite defensive layering:

```
只修真实问题：
  ✅ 逻辑错误、崩溃风险、数据损坏风险、安装失败
  ❌ 不要给每个 int() 加 try/except（Python 的 TypeError 本身就是安全降级）
  ❌ 不要给每个文件加额外备份（safe_io 已有 atomic_write）
  ❌ 不要加更多的 env var fallback 层级
  ❌ 不要引入任何新依赖
```

Without these constraints, Codex will tend to add defensive wrappers around
every operation — type checks, backup copies, extra env var chains — which adds
noise without improving safety. The skill already has safe_io for atomic writes,
fcntl locks for thread safety, and Python's own exception hierarchy for error
handling. Adding more layers is "叠甲" — stacking armor that doesn't help.

These rules also cap iteration: "最多 3 轮，第 3 轮还有问题标注'可接受风险'".
This prevents the audit from becoming an infinite loop of finding increasingly
minor issues.
