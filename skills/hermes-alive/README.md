# Hermes Alive skill bundle

This directory is the complete multi-file Hermes skill contained inside the
GitHub repository `Awenforever/hermes-alive`.

Install from the repository root:

```bash
git clone --depth 1 https://github.com/Awenforever/hermes-alive.git /tmp/hermes-alive
bash /tmp/hermes-alive/bootstrap.sh --hermes-home /opt/data
```

Or use Hermes's official GitHub skill identifier:

```bash
/opt/hermes/.venv/bin/hermes skills install \
  Awenforever/hermes-alive/skills/hermes-alive \
  --category hermes --yes
cd /opt/data/skills/hermes/hermes-alive
scripts/hermes-alive-lifecycle install
```

Provider secrets remain managed by Hermes. Run `hermes setup model` when the
lifecycle check reports that no model is configured.

## 🧬 What It Is

Hermes Alive is a zero-intrusion proactive companion skill for Hermes Agent.
It installs as a Hermes gateway hook, runs as a background `asyncio` task, discovers content periodically, composes Chinese messages with an LLM, and pushes them to WeChat.

It is not a chatbot. It does not ask questions, provide advice, report weather, or maintain conversational obligations.

> **Design core:** "A person responsible for nothing."
> The LLM owns creative expression. Code enforces only hard constraints.

---

## 🧭 Architecture

```text
Hook (gateway:startup) -> ProactivePlatformWatcher (asyncio)
  tick() every 300s
  ├─ voice.load()           -> Personality Genome (9 dimensions)
  ├─ activity guard         -> skip if conversation not silent 30+ min
  ├─ cooldown.check()       -> dynamic interval driven by social_urge
  ├─ discovery.collect()    -> 10 content sources, every 4h
  ├─ dream.run_cycle()      -> memory consolidation, every 24h
  └─ LLM.compose()          -> message(s) -> WeChat push
```

---

## 🔥 Core Features

| Feature | Behavior |
|---|---|
| 🧠 Personality Genome | 9-dimensional voice vector with event-driven evolution. |
| ⏱️ Voice-linked Cooldown | `social_urge` controls send interval: `max(30, 120 - urge × 90)` minutes. |
| 🛑 Activity Guard | Sends only when idle: Hermes not working, last message by Hermes, conversation silent 30+ min. |
| 🌐 Discovery Mesh | Collects from arXiv, GitHub, HN, V2EX, Bilibili, SSPAI, Zhihu, papers.cool, Jandan, Xiaohongshu. |
| 🧩 Context Freshness | Cosine decay over 30min-6h: `1.0 -> ~0.7 -> 0`. |
| 💬 Multi-message Burst | LLM may emit 1-5 messages separated by `---`, sent 2-5 seconds apart. |
| 🌙 Claude Dreaming | 4-stage memory cycle: Orient -> Gather -> Consolidate -> Prune. |
| 📝 Dream Auto-apply | High-confidence operations (`>=0.7`) write directly to `MEMORY.md` and affect voice genome. |
| 🔎 Pipeline Trace | One `tick_id` links discovery, composition, and delivery logs. |

---

## 🧱 Module Map

| Module | Responsibility |
|---|---|
| `voice_engine.py` | Personality Genome, 9D voice vector, event evolution, social urge. |
| `proactive_watcher.py` | Main loop, burst sending, pipeline logs, activity guard. |
| `discovery.py` | 10-platform content discovery. |
| `llm_message_composer.py` | Prompt construction, sanitizer, multi-message splitting. |
| `context_tracker.py` | Cross-session context tracking and cosine freshness decay. |
| `dream_engine.py` | 4-stage Claude Dreaming memory consolidation. |
| `cooldown_manager.py` | Dynamic cooldown from `social_urge`. |
| `handler.py` | Hook dispatch: `startup`, `session:start`, `agent:end`. |
| `safe_io.py` | Thread-safe I/O with `fcntl` locks and atomic writes. |
| `dream_prompt.py` | Dream prompt templates. |
| `dream_diff_store.py` | Dream diff persistence. |
| `log_rotate.py` | Daily log rotation, 7-day retention. |
| `alive_control.py` | Runtime lifecycle control. |

---

## ⚙️ Configuration

| Key | Required | Default | Purpose |
|---|---|---|---|
| `HERMES_PROACTIVE_PLATFORM_ENABLED` | Yes | `false` | Master enable. |
| `HERMES_PROACTIVE_WEIXIN_CHAT_ID` | Yes | — | Target WeChat chat ID. |
| `TZ` | Yes | — | Your timezone (e.g. `Asia/Shanghai`, `America/New_York`). |
| `VOICE_ENABLED` | No | `false` | Personality Genome. |
| `HERMES_DREAM_ENABLED` | No | `false` | Dream memory consolidation. |
| `HERMES_PROACTIVE_LAT` | No | — | Latitude for weather (optional). |
| `HERMES_PROACTIVE_LON` | No | — | Longitude for weather (optional). |
| Quiet hours | Built-in | `00:30-08:30` | No proactive messages during this window (your local time). |

---

## 🧠 Design Principles

### 1. LLM Owns Content

Prompt controls voice, rhythm, topics, and intent. The sanitizer blocks only empty messages and overlong output.

### 2. Code Owns Hard Constraints

Python handles lifecycle, cooldowns, quiet hours, activity guard, delivery, persistence, and log traceability.

### 3. No Conversation Duty

Hermes Alive does not ask, suggest, check in, explain itself, or optimize for helpfulness. Self-expression comes first.

### 4. User Silence Is a Boundary

The watcher skips the whole tick unless:
- Hermes is NOT currently executing a task (session is idle), AND
- Hermes sent the last message, AND
- The entire conversation has been silent for 30+ minutes.

### 5. Memory Changes Behavior

Dream output is not decorative. High-confidence memory diffs are applied to `MEMORY.md`, then reflected by the voice genome.

---

## 🧩 Extension Points

| Area | Where to Extend |
|---|---|
| New content source | Add collector logic in `discovery.py`. |
| Voice dynamics | Extend genome dimensions or event rules in `voice_engine.py`. |
| Message policy | Modify prompt templates and sanitizer in `llm_message_composer.py`. |
| Memory behavior | Tune cycle stages in `dream_engine.py` and templates in `dream_prompt.py`. |
| Runtime controls | Add lifecycle commands in `alive_control.py`. |

---

## 📜 License

MIT — see [LICENSE](./LICENSE).
---

## GitHub self-install / configure / verify / uninstall contract

The complete GitHub repository is the distribution unit.

```bash
git clone --depth 1 \
  https://github.com/Awenforever/hermes-alive.git \
  /tmp/hermes-alive

bash /tmp/hermes-alive/bootstrap.sh \
  --hermes-home /opt/data
```

The bootstrap atomically installs:

- source skill: `/opt/data/skills/hermes/hermes-alive`;
- active hook: `/opt/data/hooks/hermes-alive`;
- persistent managed configuration and learning state:
  `/opt/data/hermes_alive_shared`.

Provider credentials remain owned by Hermes:

```bash
LIFECYCLE=/opt/data/skills/hermes/hermes-alive/scripts/hermes-alive-lifecycle

"$LIFECYCLE" configure --provider-check-only
/opt/hermes/.venv/bin/hermes setup model
```

Configure only non-secret personalization:

```bash
"$LIFECYCLE" configure \
  --enable \
  --weixin-chat-id '<chat-id>' \
  --timezone Asia/Singapore \
  --quiet-start 23:00 \
  --quiet-end 08:00 \
  --emoji-policy contextual

"$LIFECYCLE" verify
"$LIFECYCLE" status
```

Explicit process environment variables override managed values. API keys must
not be stored in Hermes Alive configuration.

Default uninstall removes the source skill, active hook and managed
configuration while preserving learning/runtime state:

```bash
"$LIFECYCLE" uninstall
```

Purge is destructive and removes all Hermes Alive shared state:

```bash
"$LIFECYCLE" purge
```

A changed hook may require a gateway restart, but production restart and real
message delivery require explicit approval.

Troubleshooting:

```bash
"$LIFECYCLE" status
"$LIFECYCLE" verify
python3 /opt/data/skills/hermes/hermes-alive/tests/run_matrix.py
python3 /opt/data/skills/hermes/hermes-alive/tests/run_stress.py
```

Required hook events: `gateway:startup`, `session:start`, `agent:end`.

Startup-ready notifications are owned by `hermes-wechat-enhance`, not Hermes
Alive. Hermes Alive may observe lifecycle events, but must not send Gateway
online / Hermes ready / startup-ready notifications.

---

## ENV_AWARE_PERSISTENCE_CONTRACT_V1

This skill is environment-aware for persistence.

- Bare WSL/Linux: Docker volume checks are not required.
- Docker/container: `HERMES_HOME` should be the persistent mounted Hermes data root, normally `/opt/data`.
- Source and active hooks may be replaced during install/upgrade.
- User/runtime state must be kept outside source and preserved across container rebuilds.
- Uninstall preserves user/runtime state by default.
- Destructive user data deletion requires explicit confirmation such as `DELETE_USER_DATA`.

Verify:

```bash
python3 scripts/verify-persistence.py
```

## STYLE_GUARD_PROMPT_AND_POSTPROCESS_V1

Hermes Alive includes a lightweight style guard for proactive messages. It reads recent proactive sends and recent conversation context to reduce repeated “刚……” openers, relax overly formal punctuation, allow low-frequency natural emoji, add light ignored-message emotion, and avoid out-of-context chatter during debug / production workflows.

## STYLE_GUARD_CONTENT_CONTEXT_V1

Hermes Alive V1.2 makes content-sharing proactive messages less vague. If it shares a real news/paper/project/tool/link item, it should explain why the item is interesting or weird and include a source link when available. Content shares may be sent as multiple WeChat bubbles using `---`.

## Phase H test suites

Markers: `HERMES_ALIVE_MATRIX_SUITE_V1` and `HERMES_ALIVE_STRESS_SUITE_V1`.

```bash
python3 skills/hermes-alive/tests/run_matrix.py
python3 skills/hermes-alive/tests/run_stress.py
```

Final acceptance must use the default full stress scale. Reduced scale is developer smoke only.
