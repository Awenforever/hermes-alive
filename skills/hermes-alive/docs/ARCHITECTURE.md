# Architecture

## Runtime flow

```text
gateway:startup
  -> handler
  -> ProactivePlatformWatcher
      -> control and hard-exempt system work
      -> activity/context snapshot and lease
      -> Circadian decision (shadow or live)
      -> dynamic Sleep/Quiet comparison/enforcement
      -> live Circadian pre-compose gate
      -> cooldown and interruption policy
      -> legacy fixed quiet override only when live dynamic-awake is authoritative
      -> discovery and dream cycles
      -> LLM composition
      -> live proactive quality audit/enforcement
      -> per-send activity/context guard
      -> WeChat delivery and delivery commit/release
```

The managed lifecycle defaults the proactive quality governor to `enforce` and
Circadian to `live`. In live mode, dynamic sleep state is authoritative for
proactive-social quiet behavior. Legacy fixed quiet hours remain available as
comparison/rollback evidence and as the active safeguard when Circadian is
`shadow` or `off`.

## Main components

| Component | Responsibility |
|---|---|
| `handler.py` | Hook dispatch and lifecycle integration. |
| `proactive_watcher.py` | Decision ordering, composition, enforcement, delivery, and observability. |
| `context_tracker.py` | Bounded context, last-speaker state, activity lease, and send-time guards. |
| `alive_state.py` | Interaction evidence, current flow, recent speech acts, and bounded mood state. |
| `proactive_disposition.py` | Personality-informed willingness/restraint without a normal fixed unanswered switch. |
| `voice_engine.py` | Bounded voice profile and reversible adaptation. |
| `interest_learning.py` | Attributed, reversible interest updates. |
| `discovery.py` | Collection, ranking, cached-candidate rotation, and validated content references. |
| `topic_dedup.py` | Persistent URL/topic reservation, delivery history, material-update fingerprints, and privacy-safe hashes. |
| `circadian_engine.py` | Sleep/wake facts, phases, sleep debt, bounded learning, and persistence. |
| `circadian_intent_bridge.py` | Deterministic recognition of fresh Hermes-directed sleep/wake instructions. |
| `circadian_sleep_quiet_policy.py` | Shadow comparison plus production live dynamic Sleep/Quiet enforcement and legacy-quiet supersession evidence. |
| `interruption_policy.py` | Social interruption level, semantic bubble budget, and content constraints. |
| `proactive_quality_governor.py` | Repeat, affect, task-evidence, topic, and weather-perspective audits. |
| `isolated_enforcement.py` | Dual-key acceptance-only enforcement for dynamic sleep/quality integration tests. |
| `location_weather_profile.py` | Optional confirmed location onboarding and local profile storage. |
| `llm_message_composer.py` | Prompt construction, structured content references, weather context, and sanitization. |
| `content_delivery.py` | Capability-aware text/link/image/file delivery with safe fallbacks. |
| `managed_config.py` | Non-secret managed configuration and environment export. |
| `safe_io.py` | Atomic writes, locks, bounded JSONL, and shared-path ownership. |

## Decision ownership

- The model owns wording and style inside structured constraints.
- Code owns lifecycle, quiet hours, cooldowns, evidence gates, state, and delivery
  success semantics.
- Control and system-critical messages are processed before social gates.
- A failed `SendResult` is a failed delivery and releases any topic reservation.
- Model-authored messages retain the real routed model in footer metadata.
- Deterministic lifecycle/control/system messages use Hermes system metadata.

## Context and activity boundaries

A proactive action checks activity and context before composition and again
before every text or rich-content send. Recent user activity, a fresh task flow,
or a conflicting context lease can cancel delivery.

Context state is bounded. Ordinary inbound messages provide new evidence but do
not mechanically erase relationship state. `/continue` and control messages do
not create a new conversational referent.

## Discovery lifecycle

```text
collect batch
  -> normalize and rank
  -> filter delivered/reserved/duplicate topic units
  -> expose eligible cached candidates
  -> share one candidate
  -> commit delivery or release reservation
  -> next eligible tick selects another unseen candidate
```

The complete in-memory collection cache is retained for diagnostics. Every cache
read revalidates eligibility against persistent topic history. Exhausted caches
produce no external share instead of replaying an old item. A delivered topic
can re-enter only when a verified material-update fingerprint changes.

## Enforcement modes

### Proactive quality

Managed configuration supports `off`, `shadow`, and `enforce`. Lifecycle default
is `enforce`. In enforce mode, missing or mismatched candidate audits fail closed
for that candidate rather than silently degrading to observe-only.

### Circadian and dynamic Sleep/Quiet

Circadian lifecycle default is `live`. In live mode, protected sleep phases
block proactive-social delivery before composition; dynamic awake state may
supersede fixed quiet hours. Unknown/corrupt live state fails closed. In
`shadow`, the same decisions are logged without changing delivery and fixed
quiet hours remain authoritative.

### Isolated dual-key guard

Acceptance-only dynamic enforcement requires both:

```text
HERMES_ALIVE_DELIVERY_ENFORCEMENT_MODE=isolated
HERMES_ALIVE_RUNTIME_SCOPE=isolated_test
```

This guard is test-only and is not exposed as managed production readiness.
