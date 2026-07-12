<div align="center">

# Hermes Alive

**A gateway-native proactive AI companion for Hermes Agent.**

Personality, context, memory, circadian rhythm, and safe lifecycle management — built to make Hermes feel present without turning every silence into a notification.

![version](https://img.shields.io/badge/version-v2.4.0-blue)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)
![Hermes](https://img.shields.io/badge/Hermes-gateway--native-6f42c1)
![status](https://img.shields.io/badge/status-acceptance%20candidate-orange)
![license](https://img.shields.io/badge/license-MIT-green)

[中文文档](./README_CN.md) · [Security](./SECURITY.md) · [Contributing](./CONTRIBUTING.md)

</div>

---

## 🧬 What Hermes Alive Is

Hermes Alive is a proactive companion layer for [Hermes Agent](https://github.com/NousResearch/hermes-agent).

It installs as a gateway hook, runs as a persistent `asyncio` task, follows the current WeChat conversation, learns a bounded personality profile, discovers potentially interesting content, and composes occasional messages through the model already configured in Hermes.

It is designed around one idea:

> **Presence without obligation.**
> Hermes may notice, remember, react, go quiet, sleep, wake, and occasionally start a conversation — but it should not demand attention or pretend to have experiences it cannot have.

Hermes Alive is not a replacement chatbot and does not own Provider credentials. It extends an existing Hermes installation while keeping model configuration, platform adapters, and message delivery under Hermes control.

---

## ✨ Core Capabilities

| Capability | What it does | Current rollout |
|---|---|---|
| 🫀 Gateway-native watcher | Runs with the Hermes gateway and evaluates proactive opportunities on a periodic tick. | Active |
| 🛑 Activity guard | Suppresses proactive output while Hermes is working, while the user is waiting for a reply, or while the conversation is still fresh. | Active |
| 🧩 Context Queue | Refreshes recent WeChat context from `state.db` and persists a bounded crash-recovery queue. | Active |
| 🧠 Personality Genome | Maintains a bounded per-user voice profile and an independent `social_urge` used for timing. | Active |
| 🌙 Circadian Engine | Models awake, drowsy, delayed sleep, sleeping, light sleep, awakened, snoozing, sleep debt, and recovery. | Shadow by default |
| 🤫 Sleep / Quiet Policy | Compares dynamic sleep state with the legacy quiet window while preserving hard system exemptions. | Shadow by default |
| 💬 Proactive Quality Governor | Detects semantic repetition, unsupported task-state claims, overused speech acts, and false weather embodiment. | Shadow by default |
| 😒 Affective pulse | Allows a low-probability, mild, one-time reaction when a real casual conversation is suddenly abandoned — never repeated or escalated for the same silence event. | Shadow by default |
| 🌦️ Fine-grained weather context | Confirms a district, county, planning area, or equivalent local region before weather is used. | Active onboarding |
| 🌐 Discovery Mesh | Collects selected content from academic, developer, news, video, and lifestyle sources with caching and budgets. | Active |
| 🌙 Dream consolidation | Reads real session context, proposes bounded memory changes, and can update the voice profile. | Optional |
| 🖼️ Rich delivery | Supports validated content references and safe media/link delivery through adapter capabilities. | Active |
| 🔎 Pipeline trace | Links discovery, composition, policy, and delivery decisions through a shared `tick_id`. | Active |
| 🧰 Lifecycle management | Atomic install, rollback, verification, state-preserving uninstall, and destructive purge. | Active |

> **Why “shadow by default”?**
> The v2.4.0 candidate records Circadian and Quality decisions without changing production delivery. Real blocking is guarded by two isolated-test-only keys until fresh-container and real spare-WeChat acceptance are complete.

---

## 🧭 How a Proactive Message Is Decided

```text
Gateway control queue
  └─ system / safety / reminder / lifecycle messages keep hard priority

Recent WeChat context
  ├─ Is Hermes still executing a task?
  ├─ Is the user waiting for Hermes to reply?
  └─ Has the conversation been quiet long enough?

Circadian Engine
  ├─ awake / drowsy / delayed_sleep
  ├─ sleeping / light_sleep / awakened / snoozing
  └─ sleep_deprived / recovering

Sleep & Quiet Policy
  ├─ dynamic sleep recommendation
  ├─ legacy quiet-window comparison
  └─ hard exemptions remain available

Proactive Quality Governor
  ├─ unanswered-message budget
  ├─ one-time affective pulse
  ├─ semantic novelty and template-family cooldown
  ├─ task-state evidence gate
  └─ weather-perspective guard

Context providers
  ├─ Personality Genome
  ├─ recent conversation
  ├─ discovery items
  ├─ confirmed local weather
  └─ learned interests and memory

LLM Composer
  └─ candidate message(s)

Post-generation guard
  └─ safe, non-duplicate, evidence-grounded output

WeChat adapter
  └─ real model metadata and traceable delivery
```

Control, safety, reminder, lifecycle, and other system-class messages are not treated as ordinary social interruptions.

---

## 🌙 Circadian Rhythm, Sleep, and Quiet Time

The Circadian Engine is more than a fixed “do not disturb” interval. It maintains a deterministic daily plan and a persistent state that can respond to explicit user intent.

Examples the intent bridge can distinguish:

| User expression | Interpretation |
|---|---|
| “晚安”“你先睡吧” | Hermes may move toward sleep earlier. |
| “再陪我一会儿” | Delay sleep temporarily, within a bounded maximum. |
| “醒醒”“起床了” | Wake early or leave sleep state. |
| “你睡了吗” | A question about state; it does not automatically rewrite the schedule. |
| “我今晚熬夜”“我还在忙” | User context only; it does not mean Hermes must stay awake. |

The model supports:

- configurable base sleep and wake times;
- bounded day-to-day variation;
- deep-sleep core time;
- minimum and ideal sleep duration;
- sleep debt and recovery;
- slow, capped learning from repeated behavior;
- decay of old learned offsets;
- explicit user requests weighted more strongly than one-off late interactions;
- wake and sleep transition messages with configurable probabilities.

A single late night must not permanently move the schedule. Repeated behavior may shift it slowly, and old shifts can decay back toward the explicit preference.

---

## 💬 Human-like Emotion Without Repetition

Hermes Alive may occasionally react when an active casual conversation suddenly stops. That is intentional: total emotional neutrality feels mechanical.

The rule is not “silence is forbidden.” The rule is:

```text
one silence episode
→ maybe one mild affective pulse
→ emotion decays
→ quiet waiting
```

For the same silence event, Hermes must not:

- send another complaint;
- escalate from mild annoyance to stronger pressure;
- repeat “人呢 / 又消失 / 呵” through paraphrases;
- continue for hours because the user did not answer;
- interpret a running script, audit, or debug workflow as personal rejection.

The Quality Governor also rejects unsupported task-state claims such as “还没跑完？” unless there is fresh structured evidence that a task is still running.

---

## 🌦️ Location and Weather, With Honest Perspective

Weather is a lightweight context provider, not the main onboarding experience.

Installation itself is zero-touch. Hermes Alive detects timezone locally, applies default quiet hours, and may prepare one network-assisted weather suggestion. The terminal never asks the user to enter a timezone, quiet-hour syntax, or weather coordinates.

When no confirmed weather profile exists, Hermes may ask one short question in the normal chat, for example:

> “I roughly place you near Tampines from the system timezone and network exit. Should I use that for local weather? If not, just tell me your district or county.”

The user may confirm, correct the district/county-level area, or decline weather context. Installation does not block while waiting for the answer, and weather stays disabled until confirmation. Network location can be wrong because of VPNs, proxies, mobile routing, or remote servers.

Privacy behavior:

- the final confirmed location is stored locally;
- raw public IP and raw lookup responses are not retained;
- Provider secrets and chat content are not sent to the weather service;
- weather queries use only the minimum region or coordinate data required by the selected provider;
- a confirmed location is not silently overwritten when the network exit changes.

Hermes may say:

> “It looks like rain for most of the week.”
> “Another rainy afternoon — take an umbrella if you’re going out.”

Hermes must not pretend:

> “It’s raining where I am.”
> “The storm is making it hard for me to breathe.”

Personality is welcome; fabricated physical experience is not.

---

## ⚡ Quick Start

The complete GitHub repository is the distribution unit. Do not install only `SKILL.md`.

### Option A — Clone and bootstrap

```bash
git clone --depth 1 \
  https://github.com/Awenforever/hermes-alive.git \
  /tmp/hermes-alive

bash /tmp/hermes-alive/bootstrap.sh \
  --hermes-home /opt/data
```

### Option B — Hermes GitHub skill transport

```bash
/opt/hermes/.venv/bin/hermes skills install \
  Awenforever/hermes-alive/skills/hermes-alive \
  --category hermes \
  --yes

cd /opt/data/skills/hermes/hermes-alive
scripts/hermes-alive-lifecycle install
```

### Automatic configuration

Hermes already owns Provider credentials and model selection. Installing Hermes Alive does not launch another Provider wizard.

```bash
LIFECYCLE=/opt/data/skills/hermes/hermes-alive/scripts/hermes-alive-lifecycle

"$LIFECYCLE" configure --provider-check-only

"$LIFECYCLE" configure \
  --non-interactive \
  --enable \
  --llm-enabled \
  --discovery-enabled \
  --dream-enabled \
  --circadian-enabled \
  --circadian-mode shadow \
  --allow-network-location

"$LIFECYCLE" verify
"$LIFECYCLE" status
```

The lifecycle command automatically detects timezone, applies the default quiet window (`23:00`–`08:00`), and prints a structured `onboarding_json` result for Hermes. If a weather location still needs confirmation, Hermes asks once in the existing chat. Users never need to type timezone identifiers, quiet-hour values, CLI flags, or coordinates.

A changed active hook may require a gateway restart. Restarting a production gateway or sending a real message should always be an explicit operational decision, not an automatic installation side effect.

---

## ⚙️ Configuration

Normal installation is conversational and automatic:

- Hermes verifies that its existing Provider is usable;
- timezone is detected from the Hermes environment and local system;
- quiet hours default to `23:00`–`08:00`;
- Circadian starts from safe defaults and learns gradually;
- optional weather context requires at most one natural chat confirmation;
- no terminal questionnaire is shown.

Advanced operators may still override non-secret settings explicitly:

```bash
"$LIFECYCLE" configure \
  --non-interactive \
  --enable \
  --timezone Asia/Singapore \
  --quiet-start 23:00 \
  --quiet-end 08:00 \
  --emoji-policy contextual \
  --circadian-enabled \
  --circadian-mode shadow
```

---

## 🏗️ Architecture

```text
Hermes gateway
└── hooks/hermes-alive
    ├── handler.py
    │   ├── gateway:startup
    │   ├── session:start
    │   └── agent:end
    │
    ├── proactive_watcher.py
    │   ├── context/activity guard
    │   ├── Circadian shadow decision
    │   ├── Sleep / Quiet shadow comparison
    │   ├── Quality Governor shadow decision
    │   ├── discovery and dream cycles
    │   └── composition and delivery
    │
    ├── context_tracker.py
    ├── voice_engine.py
    ├── circadian_engine.py
    ├── circadian_intent_bridge.py
    ├── circadian_sleep_quiet_policy.py
    ├── proactive_quality_governor.py
    ├── location_weather_profile.py
    ├── discovery.py
    ├── dream_engine.py
    ├── llm_message_composer.py
    ├── content_delivery.py
    ├── interest_learning.py
    ├── interruption_policy.py
    └── safe_io.py
```

Persistent data is separated from replaceable source code:

```text
/opt/data/skills/hermes/hermes-alive   # source skill
/opt/data/hooks/hermes-alive           # active hook
/opt/data/hermes_alive_shared          # managed config, runtime and learning state
```

This separation lets upgrades replace code without discarding learned state.

---

## 🧱 Module Map

| Module | Responsibility |
|---|---|
| `proactive_watcher.py` | Main periodic loop, policy orchestration, composition, delivery, trace logging |
| `context_tracker.py` | Recent-message queue, `state.db` refresh, role/activity semantics |
| `voice_engine.py` | Personality Genome and social urge |
| `circadian_engine.py` | Daily plan, persistent sleep state, sleep debt, recovery, bounded learning |
| `circadian_intent_bridge.py` | Deterministic user-intent parsing with deduplication and expiry |
| `circadian_sleep_quiet_policy.py` | Dynamic sleep recommendation, legacy quiet comparison, hard exemptions |
| `proactive_quality_governor.py` | Affective pulse, semantic novelty, evidence and perspective checks |
| `location_weather_profile.py` | Fine-grained location confirmation and privacy-minimized weather context |
| `interruption_policy.py` | Social interruption level and bubble limits |
| `interest_learning.py` | Bounded, attributable interest feedback |
| `discovery.py` | Content collection, normalization, caching, and budgets |
| `dream_engine.py` | Memory consolidation and high-confidence updates |
| `llm_message_composer.py` | Prompt construction, model call, fallback, cleaning and splitting |
| `content_delivery.py` | Validated links, media references, and adapter-aware delivery |
| `managed_config.py` | Non-secret managed configuration loader |
| `safe_io.py` | Atomic writes, file locks, bounded JSON/JSONL persistence |
| `alive_control.py` | Runtime start/stop controls |
| `log_rotate.py` | Log rotation and retention |

---

## 🔎 Logs and Diagnostics

Every proactive tick is recorded in the shared runtime log with its decision, reason, and `tick_id`.

```bash
cd /opt/data/skills/hermes/hermes-alive

# Recent events with message previews
python3 scripts/logs.py --tail 5 --preview

# Sent messages since a date
python3 scripts/logs.py --decision sent --since 2026-07-01 --preview

# Decision statistics
python3 scripts/logs.py --stats

# Errors as raw JSON
python3 scripts/logs.py --decision error --json
```

Lifecycle diagnostics:

```bash
scripts/hermes-alive-lifecycle status
scripts/hermes-alive-lifecycle verify
```

---

## 🧪 Verification and Acceptance

Developer regression suite:

```bash
cd /opt/data/skills/hermes/hermes-alive
bash tests/run_all.sh
```

Focused suites:

```bash
python3 tests/run_matrix.py
python3 tests/run_stress.py
python3 tests/run_joint_shadow_replay.py
python3 tests/run_isolated_enforcement.py
```

Final acceptance is stricter than unit testing:

1. start from a fresh container;
2. clone or install from the real GitHub repository;
3. complete Provider and personalization onboarding;
4. run full matrix and default-scale stress tests;
5. exercise install, verify, uninstall, reinstall, and purge;
6. use a spare WeChat account for approved real end-to-end delivery;
7. confirm a clean uninstall and no production side effects.

The candidate must not be treated as production-ready until that sequence passes.

---

## ♻️ Lifecycle and Data Retention

```bash
LIFECYCLE=/opt/data/skills/hermes/hermes-alive/scripts/hermes-alive-lifecycle

"$LIFECYCLE" install
"$LIFECYCLE" configure
"$LIFECYCLE" verify
"$LIFECYCLE" status
"$LIFECYCLE" uninstall
"$LIFECYCLE" purge
```

- `install` performs transactional source and hook activation with rollback.
- `verify` checks manifests, source/hook parity, Python compilation, and configuration.
- `uninstall` removes source, active hook, and managed config while preserving learning/runtime state.
- `purge` removes all Hermes Alive shared state and is intentionally destructive.

---

## 📚 Documentation

- [Architecture](skills/hermes-alive/docs/ARCHITECTURE.md)
- [Runtime policies](skills/hermes-alive/docs/RUNTIME_POLICIES.md)
- [Lifecycle and persistence](skills/hermes-alive/docs/LIFECYCLE_AND_PERSISTENCE.md)
- [Data and privacy](skills/hermes-alive/docs/DATA_AND_PRIVACY.md)
- [Testing and acceptance](skills/hermes-alive/docs/TESTING_AND_ACCEPTANCE.md)
- [Discovery development](skills/hermes-alive/docs/DISCOVERY_DEVELOPMENT.md)

---

## 🛡️ Design Principles

1. **Model owns expression; code owns safety boundaries.**
2. **User silence can create a momentary emotion, not an escalating campaign.**
3. **No task-state claim without fresh evidence.**
4. **No fabricated location, weather embodiment, or physical sensation.**
5. **Explicit user preference outweighs one-off behavioral inference.**
6. **Learning is bounded, attributable, reversible, and privacy-conscious.**
7. **Replaceable source and persistent user state remain separate.**
8. **Provider secrets stay with Hermes.**
9. **Production changes are never hidden inside testing.**
10. **Fresh-container acceptance precedes production replacement.**

---

## 📜 License

MIT — see [LICENSE](./LICENSE).
