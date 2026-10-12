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
      -> discovery cycle (legacy Dream is retired and inert)
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
| `voice_engine.py` | Legacy live voice/profile adaptation; retained during shadow migration only. |
| `alive_kernel/presentation.py` | Replayable explicit presentation preferences and advisory-only inferred style. |
| `alive_kernel/disposition.py` | Post-selection, evidence-carrying expression cues with no action authority. |
| `alive_kernel/semantic_rendering.py` | Encrypted meaning atoms, deterministic fidelity proof, and fail-closed model-candidate assessment. |
| `alive_kernel/semantic_review.py` | Independent review binding, encrypted candidate/receipt persistence, explicit risk classes, and complete multilingual replay metrics. |
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

The shadow Alive kernel is deliberately separate from this legacy watcher. It
records a durable event history, projects typed memory/agenda/outcome state and
keeps model consolidation behind independent retention and learning consent.
Model-derived memory is review-only until the user explicitly accepts it. See
`ALIVE_KERNEL_PLAN.md` and ADR-0016. It does not yet drive production sends.
An existing kernel store is recovered at gateway startup in dependency order;
this replays only Alive-owned local projections and never calls a model or
performs an external action (ADR-0017).

The shadow kernel also has an unscheduled consolidation synthesizer (ADR-0018).
It gathers only consented retained evidence, calls Hermes' auxiliary model
route, validates each strict-JSON candidate independently and sends survivors
through the same review-only consolidation service. It owns no provider key or
fallback list. Raw prompts and responses are ephemeral; durable records contain
only structural receipts, actual-model attribution and encrypted proposals.

Its first integrated cognition coordinator is also unscheduled (ADR-0020). It
persists candidate framing, subject-scoped agenda/evidence checks, exploration
and a selection, but always selects structural safe silence. It performs no
provider, channel or tool operation. Model choice and action execution remain
separate future boundaries rather than hidden options on the coordinator.

An unscheduled model selector may consume a completed frame after the
exploration gate (ADR-0021). It calls Hermes' auxiliary route, exposes only
admissible candidates, records actual response-model attribution and persists
an encrypted rationale. Its output is a validated intent, not an action
attempt; it has no sender or tool-execution dependency.

Validated intent crosses a second, deterministic send-time boundary before it
can ever become an attempt (ADR-0022). That boundary rechecks latest state,
active user authority, current policy, evidence lifetime and the requested
Hermes capability. Its short-lived receipt is not execution and no production
adapter consumes it while the kernel remains in shadow.

An action attempt must consume that exact unexpired receipt (ADR-0023). The
outcome projection rechecks causal order and latest state before recording the
attempt. Startup replay projects frames before exploration, then selections,
then outcomes; this order is part of correctness, not an optimization.

Authorized attempts enter a leased SQLite dispatch outbox (ADR-0024). Workers
receive a short random lease token, never standing authority. Plaintext is
resolved from the vault only under a live token. Authenticated Hermes terminal
events close dispatch and are reconciled into outcome evidence; recovery checks
those events before ever restoring a row as pending.

Leasing and execution are separate (ADR-0026). `begin_execution` records an
authenticated start fact before returning plaintext to an adapter. A lost
worker after that point produces `uncertain`, never automatic retry. Terminal
facts bind the exact start event and lease generation, so late evidence can
resolve uncertainty without erasing the causal gap.

Start/result lookup is a rebuildable incremental projection (ADR-0029), not a
full-history scan in the acquisition path. Its row set contains only sequence,
event identity/type and attempt identity. A transaction advances rows and
checkpoint together to a captured journal watermark. Evidence is fetched from
the journal and fully re-authenticated before it can affect outbox state.
Derived rows are also keyed-authenticated; startup rebuilds the index if its
checkpoint, row count or authenticators fail validation.

Execution content is also separate from routing (ADR-0027). The only current
external schema is a bounded channel message with text and presentation format.
It cannot name a platform, profile, recipient, chat, thread or adapter. Its
installation-keyed canonical authenticator is bound into authorization and
revalidated at attempt and dispatch boundaries.

Routing is a separate authority projection (ADR-0028). A signed host snapshot
states the exact Hermes/plugin API contract and strongest receipt its public
interface can prove. A user-authorized route stores platform/profile/chat only
in the encrypted vault and exposes a keyed fingerprint to the journal. Both
the authorizer and outbox bind and revalidate the exact snapshot and route.
`PluginContext.inject_message()` on stable Hermes 0.21.6 proves only request
acceptance, so it cannot activate the external-delivery bridge.

External Discovery now has a separate shadow-kernel ingestion boundary
(ADR-0030). Collectors may report bounded observations; the boundary records
encrypted evidence and proposes an opportunity. It cannot compose, reserve,
route or send. Exact rediscovery is idempotent, material updates supersede the
prior opportunity, and source failures remain health facts. The legacy watcher
may mirror its external batch only when both the general kernel shadow flag and
the Discovery-specific shadow flag are enabled. The mirrored result is not read
back into legacy policy or delivery.

User availability is now a separate shadow-kernel projection (ADR-0031). It
accepts authenticated, expiring direct-activity, explicit-user or system-policy
signals and evaluates them independently of Circadian state. Direct activity
may block; inactivity remains unknown. Even explicit availability is context
evidence and never grants an action permit. A separate dual opt-in bridge can
mirror the legacy activity guard for comparison, but the current watcher does
not consume the projection yet. Circadian remains a legacy live gate until
shadow evaluation supports removing its authority and retaining, at most, its
optional presentation rhythm.

Presentation is also a separate shadow-kernel projection (ADR-0032). Its
resolved plan applies only same-subject, causally proven explicit user style
preferences over deterministic neutral defaults. Learned estimates and legacy
voice snapshots are advisory-only and expiring. The plan cannot establish a
fact or relationship, change message semantics, authorize an action or select
a route. Projection corruption returns neutral style until replay repair. A
dual-opt-in bridge mirrors only pseudonymous numeric legacy dimensions; the
legacy watcher never reads the projection back into composition.

Disposition is downstream of validated intent (ADR-0033). It interprets
individual risk, interruption-cost, urgency, novelty and confidence dimensions
as independent expression cues, preserving their evidence IDs instead of
blending a mood score. Silence and non-communication selections have no
renderable disposition. A consumer must prove the exact latest validated
selection, authenticate the snapshot and deterministically recompute the cues.
The snapshot cannot change selection, semantics, routing or authority and is
not connected to the production watcher.

Meaning precedes any new style renderer (ADR-0034). Bounded semantic atoms keep
raw content in the encrypted vault and expose only structural IDs/kinds and
evidence references to the journal. Critical literals are explicitly locked.
The selected deliberation candidate contains only a strict meaning-event
reference. Deterministic rendering emits atoms verbatim with formatting-only
separators and revalidates the latest selection on every receipt check.

A free model rewrite can be structurally screened but cannot prove itself
faithful. Missing protected literals are rejected; ordinary paraphrases remain
review required. ADR-0035 binds any review to the exact candidate digest and
requires a distinct execution, actual reviewer identity, independence domain,
complete per-atom findings and explicit added-claim/speech-act checks. A clean
review grants shadow-comparison eligibility only. “Fidelity proven” still
means only that deterministic rendering preserved the defined meaning;
truth/entailment, action authorization and route authorization remain separate
upstream/downstream boundaries.

Model candidates and reviews are durable but not permanently valid
(ADR-0036). Candidate plaintext stays in the erasable vault; journal events
retain its digest, exact renderer execution and structural evidence. Every
review read re-authenticates both events, decrypts and re-hashes the candidate,
reruns semantic assessment, checks current expiry and proves that the bound
selection is still latest. Meaning/candidate erasure, superseding intent,
tampering or expiry leaves history intact but invalidates current use.

External authority also depends on the latest user-owned autonomy policy
(ADR-0025). The default is no policy and therefore no proactive execution.
Authorization receipts and outbox rows bind an exact policy event/revision;
pause or later policy changes revoke queued work without reviving it on resume.

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
