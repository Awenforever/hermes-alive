---
name: hermes-alive
description: "Hermes Alive — gateway-native proactive AI companion for WeChat. Evolves a per-user Personality Genome, discovers content, generates Chinese messages via LLM, and consolidates memory through Claude Dreaming. One-command deploy: bash scripts/deploy.sh --all"
version: 2.3.0
---

# Hermes Alive

A self-contained, installable skill that turns Hermes Agent into a proactive WeChat companion. Drops into any Hermes installation — copy one directory, run one script, restart gateway.

## Quick Start

```bash
# 1. Install the skill (copy to /opt/data/skills/hermes/hermes-alive/)
# 2. Deploy + install dependencies
cd /opt/data/skills/hermes/hermes-alive
bash scripts/deploy.sh --all

# 3. Set your WeChat chat ID in /opt/data/.env:
#    HERMES_PROACTIVE_WEIXIN_CHAT_ID=<your-id>

# 4. Restart gateway
docker-compose up -d hermes

# 5. Verify
bash scripts/verify.sh
```

## What It Does

Hermes Alive adds a persistent asyncio task to your Hermes gateway that:

- **Pipeline logging** — each send is traceable: discovery → compose → sent, all linked by `tick_id`
- **Log rotation** — daily archive with configurable retention (default 7 days)
- **Query tool** — `scripts/logs.py` for filtering, stats, and preview
- **Context injection** — recent conversation injected into compose prompt with cosine freshness decay (30min–6h)
- **Multi-message burst** — LLM can compose 1-5 messages with `---` separator, sent 2-5s apart like a real person
- **Activity guard** — three-layer defense: (1) if Hermes is actively executing a task (session busy via `session:start`/`agent:end` hook state machine), suppress entirely; (2) if the last message in conversation is from user (Hermes mid-reply), suppress; (3) if any message (either side) was sent < 30 minutes ago (conversation not fully silent), suppress. Only when all three pass does a proactive message fire. This prevents Alive from interrupting long-running tasks (e.g. Codex delegations) or recently-active chats.
- **ContextQueue** — in-memory message queue (max 30) persisted to `context_queue.json`. Replaces fragile `agent:end`-dependent `recent_context.json` capture. Refreshed from `state.db` before every tick so the guard never misses user activity, even if the hook event didn't fire.
- **Voice Genome** — per-user Personality Genome stored in `voice_state.json`, evolved from user style signals and dream findings
- **Voice-linked cooldown** — dynamic spacing from independent `social_urge`: `max(30, 120 - social_urge × 90)` min
- **Dream reads sessions** — real state.db transcripts, not just static MEMORY.md
- **Dream auto-apply** — high-confidence (≥0.7) ops written directly to MEMORY.md (with backup)
- **Dream affects voice** — high-confidence academic/leisure interests nudge the Personality Genome
- **Content discovery** from 10 platforms — every 4h, with persistent disk cache and random sampling
- **LLM fallback** — if primary model fails, retry with `HERMES_PROACTIVE_LLM_FALLBACK_MODEL`
- **Discovery cache** — results persisted to `discovery_cache.json`, survives gateway restarts

## Architecture

```
Hook (gateway:startup) → ProactivePlatformWatcher (asyncio task)
  │
  tick() every 300s
  │
  ├─ voice.load()              → per-user Personality Genome + social_urge
  ├─ is_session_busy()         → skip if Hermes still executing a task
  ├─ ContextQueue.refresh()    → sync from state.db (source+user_id JOIN)
  ├─ activity guard            → three-layer: busy → user last → silence check
  ├─ cooldown.check()          → social_urge-linked dynamic spacing
  ├─ discovery.collect()       → 10 content sources (per 4h)
  ├─ dream.run_cycle()         → memory consolidation (per 24h)
  └─ LLM.compose()             → System Prompt + voice snapshot + discovery + context
       │
       └─ adapter.send()       → WeChat message(s)
```

### Content Sources

| Source | Method | Type |
|--------|--------|------|
| arXiv | aiohttp API | Academic papers |
| GitHub Trending | aiohttp API | Repositories |
| Hacker News | aiohttp API | Tech news |
| V2EX | JSON API | Chinese tech |
| Bilibili | JSON API | Popular videos |
| 少数派 | RSS 2.0 | Tech articles |
| 知乎 | Playwright | Hot list |
| papers.cool | Playwright | Paper discussions |
| 煎蛋 | Playwright | Misc interesting |
| 小红书 | Playwright + anti-detect | Lifestyle notes |

### Dream Memory Consolidation

4-phase Claude Dreaming cycle that reads real session transcripts, auto-applies high-confidence results, and shifts voice:

1. **Orient** — read MEMORY.md + proactive_context.md + recent 3-5 session transcripts from state.db
2. **Gather** — send dream prompt + all context to auxiliary LLM for analysis
3. **Consolidate** — parse operations (add/replace/remove), categorize by type and confidence
4. **Prune** — flag stale/low-trust entries

Results auto-applied to MEMORY.md for confidence ≥ 0.7; lower-confidence ops logged only.
Post-dream voice shift: high-confidence academic interests reduce absurd humor; leisure interests soften formality and increase warmth.
All logged to `proactive_log.jsonl` with `voice_after` snapshot.

## Files

```
hermes-alive/
├── SKILL.md                 ← This file
├── hooks/                   ← Gateway hook source (deployed to /opt/data/hooks/)
│   ├── HOOK.yaml
│   ├── handler.py           ← Event dispatcher (wires context_tracker on agent:end)
│   ├── proactive_watcher.py ← Main loop (multi-message burst + pipeline logging)
│   ├── discovery.py         ← Multi-platform content engine
│   ├── llm_message_composer.py ← LLM prompt + sanitize + multi-message split
│   ├── context_tracker.py   ← Captures recent conversation for freshness injection
│   ├── dream_engine.py      ← Memory consolidation
│   ├── dream_prompt.py      ← Claude Dreaming prompt
│   ├── voice_engine.py      ← Personality Genome + social_urge migration/evolution
│   ├── cooldown_manager.py  ← Rate limiting + social_urge dynamic cooldown
│   ├── dream_diff_store.py  ← Dream diff persistence
│   ├── log_rotate.py        ← Daily log rotation + retention
│   ├── safe_io.py           ← Thread-safe file I/O helpers
│   ├── alive_control.py     ← Runtime lifecycle control (enable/disable/restart)
│   └── __init__.py          ← Package marker
├── scripts/
│   ├── deploy.sh            ← One-command setup
│   ├── verify.sh            ← Health check
│   └── logs.py              ← Log query tool (filter, stats, preview)
├── templates/
│   ├── .env.template        ← Required env vars
│   └── sources.yaml         ← Content source config
└── references/
    ├── codex-patterns.md
    ├── message-style-guidelines.md   ← Discovery ref style + multi-message + context freshness
    ├── platform-discovery-patterns.md
    └── session-id-format-change.md   ← Debugging guide for activity guard failure after Hermes update
```

## Configuration

All settings via environment variables. See `templates/.env.template` for the complete list.

Key variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `HERMES_PROACTIVE_PLATFORM_ENABLED` | false | Master enable |
| `HERMES_PROACTIVE_WEIXIN_CHAT_ID` | — | Target chat (required) |
| `HERMES_PROACTIVE_PLATFORM_INTERVAL_SECONDS` | 300 | Tick interval |
| `HERMES_PROACTIVE_LLM_ENABLED` | false | Use LLM generation |
| `HERMES_PROACTIVE_LLM_MODEL` | deepseek-v4-flash-ascend | Primary model |
| `HERMES_PROACTIVE_LLM_FALLBACK_MODEL` | deepseek-v4-flash | Fallback model (official API) |
| `HERMES_PROACTIVE_LLM_TIMEOUT` | 60 | LLM call timeout (seconds) |
| `HERMES_DREAM_ENABLED` | false | Enable dream consolidation |
| `HERMES_DREAM_INTERVAL_HOURS` | 24 | Hours between dreams |
| `HERMES_PROACTIVE_COOLDOWN_MINUTES` | 120 | Base cooldown (adjusted by social_urge) |
| `HERMES_PROACTIVE_DISCOVERY_INTERVAL_SECONDS` | 14400 | Discovery interval (4h) |
| `HERMES_PROACTIVE_DISCOVERY_ENABLED` | true | Enable content discovery |
| `HERMES_PROACTIVE_QUIET_START` | 0:30 | Quiet hours start |
| `HERMES_PROACTIVE_QUIET_END` | 8:30 | Quiet hours end |
| `HERMES_ALIVE_LOG_RETENTION_DAYS` | 7 | Log archive retention |
| `PLAYWRIGHT_BROWSERS_PATH` | `/opt/data/.playwright-browsers` | Chromium location |

**Removed in v2.2**: `HERMES_PROACTIVE_ACTIVE_COOLDOWN_MINUTES` — replaced by activity guard (hard skip <30min) + voice-linked cooldown.

**Changed in v2.3**: `MOOD_ENABLED`/`COMPOSER_ENABLED`, `mood_engine.py`, `message_composer.py`, and `recent_context.json` were removed. Replaced by ContextQueue (`context_queue.json`) for activity guard and freshness injection. Session busy/idle state machine added via `session:start`/`agent:end` hooks — prevents proactive messages while Hermes is executing tasks. Activity guard upgraded from two-condition to three-layer (busy → user → silence). Deploy script now auto-detects timezone and appends all env vars. README includes AI agent installation guide.

## Logging

All watcher decisions are logged to `proactive_log.jsonl` in the shared directory. Every tick produces one JSONL entry.

**Log rotation** (`log_rotate.py`): Runs on watcher startup. Archives yesterday's log as `proactive_log.YYYY-MM-DD.jsonl`, deletes archives older than `HERMES_ALIVE_LOG_RETENTION_DAYS` (default 7).

**Query tool** (`scripts/logs.py`): Human-readable filtering and stats.

```bash
# Recent entries with message previews
python3 scripts/logs.py --tail 5 --preview

# All sent messages since a date
python3 scripts/logs.py --decision sent --since 2026-07-01 --preview

# Stats overview
python3 scripts/logs.py --stats

# Raw JSON for piping
python3 scripts/logs.py --decision error --json

# See cooldown skips
python3 scripts/logs.py --reason cooldown --tail 5
```

Available filters: `--decision` (sent/skip/dream/discovery/compose/voice_mutation/start/stop/error), `--voice`, `--since`, `--until`, `--reason`, `--tail N`, `--all`, `--preview`, `--stats`, `--json`.

## Pipeline Trace

Every sent message now has a full pipeline trace in the log. Same `tick_id` links discovery → compose → sent:

```bash
# Find a message's full pipeline
python3 scripts/logs.py --json | python3 -c "
import json,sys
[print(json.dumps(e,ensure_ascii=False,indent=2))
 for e in json.load(sys.stdin)
 if '498202be5e7c' in e.get('tick_id','')]
"
```

## Context Injection (Freshness Decay)

Recent conversation context is captured in the ContextQueue and injected into the compose prompt with cosine-based freshness:

| Time Since | Label | Weight | Effect |
|------------|-------|--------|--------|
| < 30 min | — | — | Tick suppressed (activity guard) |
| 30 min | 刚刚 | 1.0 | Alive likely to continue the thread |
| 30 min–3h | 大约一小时前 | ~0.7 | May reference if relevant |
| 3h–6h | 之前 | ~0.0 | Ignored entirely |
| > 6h | 更早 | 0 | Ignored |

Weight formula: `cos(π/2 × (t − 30min) / 330min)` for t ∈ [30min, 6h].

**Activity guard final logic (v2.3):**
1. `is_session_busy()` → suppress (Hermes working on a task)
2. No context in queue → allow (new conversation)
3. `last_message_role == "user"` → suppress (user waiting for reply)
4. `now - last_message_timestamp < 1800s` → suppress (conversation not fully silent)
5. Otherwise → allow

Key insight: "user silence" is not about the user's last message age — it's about whether the entire conversation has been idle for 30+ minutes, with Hermes as the last speaker and no active task running. The `last_message_timestamp` (from either side) is what matters, not `last_user_timestamp`.

## Design Principles

1. **Positive guidance over hard bans** — prompt defines what the persona IS, not what it ISN'T
2. **Code handles format, prompt handles content** — 3 hard-error checks only (empty, >800 chars, format leak)
3. **Non-destructive memory** — dream engine writes diffs, backs up MEMORY.md before applying
4. **Failure isolation** — dream/discovery errors don't block message sending
5. **LLM → clean → push** — "nothing负责人" philosophy: LLM owns the creative output, code only handles hard constraints. If you're adding a regex rule to the sanitizer, you're probably doing it wrong — fix the prompt instead.

## Pitfalls

- **Absolute imports only** — hook files loaded flat by `importlib`, no relative imports
- **Timezone** — set `TZ` to the system timezone or time context will be wrong. `deploy.sh` auto-detects via `timedatectl` / `/etc/timezone` / `/etc/localtime` symlink and appends to `/opt/data/.env` during `setup_env()`. Do NOT hardcode `Asia/Shanghai` — the deploy script handles detection. For weather-aware messages, optionally set `HERMES_PROACTIVE_LAT` and `HERMES_PROACTIVE_LON`.
- **Gateway restart required** — hook changes only picked up at `gateway:startup`
- **Playwright persistence** — Chromium must be on persistent volume (`/opt/data/.playwright-browsers`), Python package reinstalled after image rebuild
- **Bilibili anti-bot** — needs full browser UA, not the discovery UA
- **Activity guard vs cooldown** — <30min user activity → hard skip (no message, cooldown NOT advanced). 30min–6h → cosine context decay. >6h → no context.
- **Voice-linked cooldown** — `set_mood_cooldown(social_urge)` must be called before `can_send()` each tick. Formula: `max(30, 120 − urge × 90)`.
- **LLM fallback** — primary model failure silently retries with `HERMES_PROACTIVE_LLM_FALLBACK_MODEL` (must be set in .env). Works via `async_call_llm(task="proactive", model=fallback_model, ...)`.
- **Discovery cache** — persisted to `discovery_cache.json`. Survives restarts. Fresh data every 4h from both external + Playwright sources.
- **`.env` is protected** — cannot modify from agent context. User must manually update `/opt/data/.env` for parameter changes.
- **Footer shows "hermes" instead of model name** — Proactive messages must set `is_system: false` in metadata. When `is_system: true` (the old default from SYSTEM_METADATA), the WeChat adapter tags messages as system-origin and shows "hermes" as the footer regardless of `model_name`. The fix is in `proactive_watcher._metadata()` — it now sets `is_system = False` so the footer reflects the actual model (e.g. `deepseek-v4-flash-ascend`).

- **Never test deploy on production hooks directory** — Use env vars `HOOK_DIR` and `SHARED_DIR` to isolate tests: `HOOK_DIR=/tmp/test-hooks SHARED_DIR=/tmp/test-shared bash deploy.sh`. The deploy script respects these overrides. Accidentally `rm -rf /opt/data/hooks/hermes-alive/*` will delete the running hook's source files — the modules stay in Python's memory cache but voice_state.json and other runtime state will be lost. After restoration, verify with `ls /opt/data/hooks/hermes-alive/`.
- **Migration guard against degraded state** — `mood_state.json` values decay toward 0 over time (mechanical tick decay). When migrating to voice_state.json, values below 0.08 are treated as meaningless and skipped — the voice genome uses freshly generated defaults instead. After successful migration, the old mood file is renamed to `.migrated` to prevent re-migration on subsequent restarts. If you see voice dimensions near 0 after first startup, check that the migration guard triggered correctly.

- **ContextQueue reliability** — `context_tracker.py` refreshes from `state.db` using `WHERE source = 'weixin' AND user_id = ?` JOIN on every `activity_snapshot(refresh=True)` call. The watcher calls this before each tick's guard decision, so even if `agent:end` hook fails to fire, the queue stays current. `context_queue.json` persists to disk for crash recovery. Stale `recent_context.json` was removed in v2.3 — it is no longer written or read.

- **Lock name must match between read and write** — `_sent_count_between()` reads `proactive_log.jsonl` and must use the SAME lock name as `append_jsonl()`. The write side uses `"proactive_log.lock"` — the read side must use exactly that name, not a different name like `"proactive_log.read.lock"`. Mismatched lock names = no synchronization.

- **Voice genome floor for low-baseline dimensions** — `humor_absurd` and `self_disclosure` have low defaults (0.2) and can dip below 0.2 during initialization due to the random component. After `_clamp()`, explicitly set floor: `if dim in ("humor_absurd", "self_disclosure") and value < 0.2: value = 0.2`. Verify with 500-init stress test.

- **Footer shows real model name** — Proactive messages must set `is_system: false` in metadata so the WeChat adapter uses `model_name` for the footer tag instead of "hermes". The old `SYSTEM_METADATA` default had `is_system: true`. Fixed in `proactive_watcher._metadata()`.

- **Activity guard correct semantics** — The guard checks `last_message_timestamp` (most recent message from EITHER side), NOT `last_user_timestamp`. Checking user's last message age is wrong: if Hermes replied after a 40-min LLM delay, the user message is 40-min old but Hermes just spoke — the conversation is NOT idle. The correct check is "has the entire conversation been silent for 30+ min?" This prevents Alive from firing immediately after a delayed Hermes reply. Additionally, `is_session_busy()` (driven by `session:start`/`agent:end` hook events) blocks all proactive messages while Hermes is executing a task. If the watcher detects Hermes is mid-task, it suppresses unconditionally even if the conversation appears silent.

- **File permissions must be 644 for non-root deployment** — Hook files deployed to `/opt/data/hooks/hermes-alive/` must be world-readable (644). Files with `0600` (owner-only) or `0000` (no access) will cause `PermissionError` when the gateway runs as non-root `hermes` user. The production Docker container runs as root so issues are masked, but clean installs or user changes will break. Check with `find /opt/data/hooks/hermes-alive -name '*.py' ! -perm 644`. Fix with `chmod 644 *.py`. The `deploy.sh` script should enforce 644 during `sync_files()`.

- **Shared path env var consistency** — All runtime state paths must use `HERMES_ALIVE_SHARED_DIR` env var (default: `/opt/data/hermes_alive_shared`). `safe_io.py` was the last holdout with a hardcoded `BASE = Path("/opt/data/hermes_alive_shared")` — must be `Path(os.getenv("HERMES_ALIVE_SHARED_DIR", "/opt/data/hermes_alive_shared"))`. `handler.py` must use `_SHARED_DIR` for all path construction (e.g. `current_voice.txt`), not `Path(os.getenv("HERMES_HOME")) / "hermes_alive_shared"` concatenation. The env var used for import path bootstrap (`_SHARED_DIR = os.getenv("HERMES_ALIVE_SHARED_DIR", ...)`) should also be used for file writes — mixing env vars risks path divergence.

## Extending

To add a new content platform:
1. Research: official API → robots.txt → curl test → Playwright fallback
2. Add extractor method in `hooks/discovery.py`
3. Add site config in `templates/sources.yaml`
4. Redeploy: `bash scripts/deploy.sh`
5. See `references/platform-discovery-patterns.md` for detailed workflow

To customize the personality:
- Edit `hooks/llm_message_composer.py` SYSTEM_PROMPT
- Follow the "positive guidance" principle — don't add prohibitions
