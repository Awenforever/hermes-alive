# Architecture

## Runtime path

```text
gateway:startup
  -> handler
  -> ProactivePlatformWatcher
      -> control queue and hard-exempt system work
      -> activity/context snapshot
      -> Circadian shadow decision
      -> Sleep / Quiet shadow comparison
      -> cooldown and interruption policy
      -> discovery and dream cycles
      -> LLM composition
      -> Proactive Quality shadow audit
      -> WeChat delivery
```

The legacy fixed quiet-hours and cooldown path remains authoritative outside the
isolated acceptance runtime. Circadian, Sleep/Quiet, and Quality decisions are
recorded without changing production delivery.

## Main components

| Component | Responsibility |
|---|---|
| `handler.py` | Hook dispatch and lifecycle integration. |
| `proactive_watcher.py` | Main task, decision ordering, composition, delivery, and observability. |
| `context_tracker.py` | Bounded cross-session context and last-speaker/activity state. |
| `alive_state.py` | Persistent interaction state, flow classification, recent speech acts, and focus lock. |
| `voice_engine.py` | Personality genome and bounded voice evolution. |
| `interest_learning.py` | Attributed, reversible interest updates. |
| `circadian_engine.py` | Planned and actual sleep/wake facts, phases, sleep debt, learning, and persistence. |
| `circadian_intent_bridge.py` | Deterministic recognition of fresh explicit sleep/wake instructions. |
| `circadian_sleep_quiet_policy.py` | Shadow comparison between dynamic sleep state and fixed quiet hours. |
| `interruption_policy.py` | Social interruption level and content constraints. |
| `proactive_quality_governor.py` | Duplicate, affect, task-evidence, and weather-perspective audits. |
| `isolated_enforcement.py` | Dual-key acceptance-only delivery enforcement. |
| `location_weather_profile.py` | Confirmed fine-grained location onboarding and local profile storage. |
| `llm_message_composer.py` | Prompt construction, structured content references, weather context, and sanitization. |
| `content_delivery.py` | Capability-aware text/link/image/file delivery with safe fallbacks. |
| `managed_config.py` | Non-secret managed configuration and environment export. |
| `safe_io.py` | Atomic writes, file locks, bounded JSONL, and shared path ownership. |

## Decision ownership

- The model owns wording and style within structured constraints.
- Code owns lifecycle, quiet time, cooldowns, evidence gates, safety, state, and
  delivery success semantics.
- Control/system-critical messages are processed before social gates.
- A failed `SendResult` is a failed delivery; it must not be recorded as sent.
- LLM-authored messages retain the real routed model in footer metadata.
- Deterministic system payloads use `hermes` metadata.

## State transition boundaries

Circadian intent recognition is deterministic and processes only fresh user
messages. Queries or user self-observations such as “你睡了吗” or “我还在忙”
do not mutate Hermes' sleep state. Explicit Hermes-directed instructions such
as “你先睡吧”, “再陪我一会儿”, and “醒醒” may update shadow state.

The same user message is de-duplicated by hash and stale messages are not
applied. Raw message text is not stored in the bridge state.

## Isolated enforcement

Real delivery control is allowed only when both acceptance-only environment
values are present:

```text
HERMES_ALIVE_DELIVERY_ENFORCEMENT_MODE=isolated
HERMES_ALIVE_RUNTIME_SCOPE=isolated_test
```

In that runtime, dynamic sleep may prevent composition, a forced-awake state may
override legacy quiet hours, unanswered silence lock may suppress composition,
and rejected quality candidates may be removed before delivery. The guard is
not exposed through managed production configuration.
