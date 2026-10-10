# Hermes Alive Kernel — Living Development Plan

Status: active

Last reviewed: 2026-10-11

Current phase: Phase 4 — outcome learning and longitudinal evaluation

Working branch: `feat/alive-kernel-3`

This is a living engineering contract, not a frozen specification. It records
why Hermes Alive exists, what we currently believe, what evidence changed our
mind, and which production gates remain. Update it whenever implementation or
evaluation disproves an assumption. A change is welcome when it moves the
project closer to the North Star and preserves the invariants below.

## North Star

Hermes Alive should make Hermes a continuous, attentive and self-correcting
assistant rather than a timer that periodically generates messages.

An Alive action should arise from a traceable chain:

```text
experience -> interpretation -> memory/belief -> intent -> decision
           -> authorized action -> outcome -> reflection/learning
```

“Alive” does not claim consciousness or imitate biological needs. It means:

- continuity across turns, restarts and model changes;
- a coherent history of experiences and commitments;
- context-sensitive initiative, including the ability to remain silent;
- learning from attributable outcomes rather than invented emotion;
- explicit uncertainty, provenance and reversible memory;
- behavior that stays under the user's authority.

## Invariants

These may be refined, but must not be silently weakened.

1. **User sovereignty** — the user can inspect, correct, forget, pause and
   bound proactive behavior. Silence never incurs a social penalty.
2. **Traceability** — every external action has an event, intent, policy
   decision, authority basis and outcome.
3. **Epistemic integrity** — observation, inference, preference, commitment
   and fiction are different data types. Confidence is not evidence.
4. **Safe silence** — uncertainty, corrupt state or missing authority fails
   closed for proactive external action, not for critical system notices.
5. **Channel and model neutrality** — Hermes owns providers and delivery
   platforms. Alive consumes capabilities; it does not hard-code a provider or
   Weixin as its identity.
6. **Independent plugins** — other plugins may publish standard events, but
   Alive cannot require or reach into their private state.
7. **Durable semantics** — retries are idempotent; acknowledged delivery is
   distinct from attempted delivery; restart cannot invent or duplicate work.
8. **Reversible evolution** — migrations, learned state and policy changes
   have versioning, audit evidence and rollback paths.
9. **Bounded autonomy** — models may propose and deliberate. Deterministic
   authority, privacy, rate and risk boundaries remain outside model control.
10. **No theatrical metrics** — human-like language is allowed, but arbitrary
    `affection`, `annoyance` or “sleep” numbers cannot masquerade as facts.

## Current diagnosis (2.9.8)

What is worth preserving:

- send-time context rechecks and interruption restraint;
- acknowledged delivery semantics and topic reservations;
- discovery diversity, novelty and provenance work;
- bounded interest/voice adaptation;
- lifecycle, portability, rollback and extensive regression tests;
- explicit shadow/enforce modes.

What must change:

- a polling pipeline currently substitutes for persistent intention;
- experience is split across unrelated JSON/JSONL files;
- the 3,000-line watcher owns scheduling, cognition, policy and execution;
- mood is produced by hand-tuned arithmetic and can punish non-response;
- dream consolidation can turn model confidence into direct memory mutation;
- there is no first-class agenda, commitment ledger or outcome-learning loop;
- tests prove many rules, but not longitudinal usefulness or coherence.

## Target kernel

```text
Hermes and plugin events
        |
        v
Durable Experience Journal  ---> privacy/redaction boundary
        |
        v
Typed Memory and Belief Store <--- contradiction + expiry + correction
        |
        v
Opportunity Generators ---> Persistent Agenda / Commitments
        |                         |
        +------------+------------+
                     v
       Deliberation (value, urgency, novelty,
       confidence, interruption cost and risk)
                     |
                     v
       Deterministic authority and safety gate
                     |
                     v
          Hermes capability / channel action
                     |
                     v
             Outcome and reflection
```

The kernel is intentionally small. Discovery, Circadian, voice, weather and
future faculties become adapters or opportunity generators, not owners of the
main loop.

## Delivery phases and exit gates

### Phase 0 — Baseline and preservation

- [x] Record the North Star and invariants.
- [x] Preserve the working 2.9.8 behavior on a separate branch.
- [ ] Capture a replay corpus from sanitized historical events.
- [ ] Define longitudinal quality and interruption metrics.

Exit: old behavior can be replayed and scored without sending messages.

### Phase 1 — Durable experience journal

- [x] Define a typed event envelope with causation and correlation identity.
- [x] Add an append-only SQLite journal with idempotent append.
- [x] Add integrity hashes and monotonic consumer checkpoints.
- [x] Add a first privacy boundary for structural lifecycle/session events;
  conversation content remains excluded until typed retention policy exists.
- [x] Add privacy-bounded structural adapters for official Hermes lifecycle,
  inbound/outbound turn and tool-round hooks, including persistent causal turn
  linkage and crash interruption facts (ADR-0013).
- [x] Add per-user, Hermes-authorized, expiry-bounded and erasable conversation
  content retention while keeping fresh installs structural-only (ADR-0014).
- [x] Add privacy-bounded native tool receipts. Treat ordinary prose-derived
  `ok/error` classifications as `outcome=unknown`; learn only from explicit
  executor terminal facts until Hermes exposes effect proof (ADR-0015).
- [x] Add opt-in shadow mirroring that cannot influence legacy decisions.

Exit: restart/replay reconstructs the same ordered experience stream, duplicate
ingestion is harmless, and no secret-bearing payload crosses ingestion policy.

### Phase 2 — Typed memory and beliefs

- [x] Define memory kinds, authority classes, lifecycle states and admission
  principles; see `adr/0002-typed-memory-is-a-projection.md`.
- [x] Implement episodic, semantic, preference, commitment and self-model
  records with provenance, confidence, validity, sensitivity and supersession.
- [x] Retrieve by relevance, importance, recency and authority without losing
  provenance; BM25 + explainable RRF is the deterministic baseline (ADR-0005).
- [ ] Make correction, forgetting and privacy erasure propagate predictably
  (encrypted content-vault primitive and resumable managed-backup purge pass;
  reference-only memory events and replay-safe item/subject forgetting pass;
  WSL, lifecycle and operator-control proof remain).
- [x] Retire direct Dream mutation and replace it with separately consented,
  evidence-bound, expiring memory proposals that require explicit user review
  before activation (ADR-0016). Automated synthesis remains shadow/off until
  longitudinal quality evidence exists.

Exit: every retrieved memory explains why it exists; contradictions and user
corrections are represented rather than overwritten.

### Phase 3 — Agenda, intentions and deliberation

- [x] Add durable commitments and opportunity records (ADR-0006; shadow-only
  authority, lifecycle, encrypted content and replay baseline implemented).
- [x] Generate multiple typed candidate actions, including deliberate silence;
  candidate sets and their encrypted explanations now replay durably.
- [x] Evaluate user value, urgency, novelty, confidence, interruption cost,
  risk and authority separately without an opaque weighted score (ADR-0007).
- [x] Let the model deliberate within structured bounds; keep policy external.
  Frames, rationales, policy rejections and validated choices now have an
  encrypted, deterministic replay projection; provider execution remains off.
- [ ] Run the new decision engine in shadow against production events.

Exit: every proposed action has a stable reason and every rejection is
inspectable; replay is deterministic outside explicitly recorded model calls.

### Phase 4 — Outcomes, reflection and learning

- [x] Link action attempts and evidence-backed delivery, reply, correction,
  feedback and downstream task outcomes to validated selections (ADR-0008).
- [x] Learn timing, topic, presentation and interruption estimates from bounded,
  expiring, retractable reviewed evidence without overriding explicit memory
  preferences (ADR-0010).
- [x] Treat no reply as ambiguous, never as punishment evidence; absence is
  intentionally not representable as an outcome kind.
- [x] Store reflections as evidence-backed proposals with bounded expiry,
  explicit user review and retractable acceptance (ADR-0009).
- [x] Add constrained exploration budgets, delivered-exposure history and
  topic/source anti-echo-chamber gates that can only narrow base policy
  (ADR-0011).
- [x] Add time-separated factual replay evaluation that rejects future
  evidence, preserves unknown feedback and forbids unsupported counterfactual
  policy claims (ADR-0012).

Exit: learning improves held-out replay metrics without increasing interruption,
factual error or user-control violations.

### Phase 5 — Faculty migration

- [ ] Port Discovery as an opportunity generator.
- [ ] Split user availability from optional character-like Circadian styling.
- [ ] Port voice as presentation policy, not a truth source.
- [ ] Replace heuristic mood with explainable dispositions.
- [ ] Retire the monolithic watcher after parity and rollback drills.

Exit: legacy runtime can be disabled with feature parity, improved evaluation
and a one-command rollback.

### Phase 6 — Production qualification

- [ ] Fresh install, upgrade, uninstall/reinstall and data migration matrices.
- [ ] Linux, Windows, WSL and Docker/NAS lifecycle verification.
- [ ] Provider and channel substitution tests owned by Hermes capabilities.
- [ ] Crash, duplicate event, partial send and corrupt-state fault injection.
- [ ] Longitudinal shadow evaluation followed by bounded live canary.
- [ ] User-facing inspect/correct/forget/pause controls.

Exit: controlled production canary passes, rollback is proven, and the user
accepts the observed long-term behavior rather than only isolated messages.

## Quality measures

Track trends and distributions, not a single synthetic “alive score”.

- useful proactive outcome rate;
- interruption regret and immediate-dismissal rate;
- unsupported factual claim rate;
- commitment completion and stale-commitment rate;
- duplicate topic/action rate;
- memory provenance and correction accuracy;
- silence quality (messages correctly not sent);
- restart/replay divergence;
- policy-denied and authority-ambiguous actions;
- user inspection, correction and disable friction;
- latency, model calls, token cost and storage growth.

## Assumption register

| ID | Current hypothesis | How it can be disproved | Status |
|---|---|---|---|
| H1 | An append-only local journal is sufficient before adopting a distributed workflow engine. | Multi-process/device recovery cannot be made correct with SQLite leases and idempotency. | Active |
| H2 | Existing faculties can migrate behind event/opportunity interfaces without a big-bang rewrite. | Shadow parity requires preserving watcher-internal coupling. | Active |
| H3 | Explainable dispositions outperform hand-authored pseudo-emotions in longitudinal coherence. | Blinded replay and live feedback show lower naturalness without safety gain. | Active |
| H4 | Model deliberation plus deterministic authority gates gives better initiative than either rules or a model alone. | Shadow evaluation shows no useful gain or unacceptable variance/cost. | Active |
| H5 | Other Hermes plugins can remain independent while publishing optional standard events. | Hermes lacks a stable event/capability boundary and adapters become private coupling. | Active |
| H6 | A portable local content vault plus coordinated managed-backup retention can give an honest, useful forgetting boundary without claiming control over arbitrary external copies. | Recovery drills cannot reconcile deletion with useful backups, or operators routinely bypass the managed boundary. | Active |

## Decision and revision protocol

For each material change:

1. reread the North Star and invariants;
2. state the hypothesis and observable success/failure criteria;
3. add or amend an ADR for structural choices;
4. implement behind a versioned or shadow boundary;
5. test replay, faults, privacy, migration and rollback;
6. record evidence, surprises and rejected approaches;
7. update this plan, including changes of direction;
8. do not equate code presence with runtime correctness.

## Change log

### 2026-10-09 — Kernel exploration begins

- Reframed Alive from proactive messaging to continuous experience, intention,
  authorized action and outcome learning.
- Chose an append-only local journal as the first substrate; see
  `adr/0001-durable-experience-journal.md`.
- Kept 2.9.8 behavior untouched while the kernel develops in shadow.
- The first Windows contract run exposed that SQLite transaction contexts do
  not close file handles. The journal now owns explicit connection closure;
  Windows file lifecycle remains a mandatory portability gate.
- Review found that a frozen envelope could still expose mutable nested payload
  values. Payloads are now recursively immutable and detached from caller-owned
  objects; concurrent duplicate ingestion is a required idempotency contract.
- Added an installation-local HMAC identity boundary. Initial shadow ingestion
  records hook structure and pseudonymous linkage, never raw message content,
  credentials or external platform IDs. It defaults off until deployment
  acceptance explicitly enables it.
- Defined typed memory as a replayable projection. Model confidence is now
  explicitly rejected as a promotion authority; raw conversation ingestion
  remains blocked until real erasure semantics exist.
- Phase-1 journal/privacy contracts passed repeatedly on Windows and as part of
  the complete Linux suite. The full-scale Linux stress run also passed: 32
  concurrent safe-I/O workers, 6,000 interest deliveries, 4,000 feedback
  updates, 10,000 delivery plans, 10,000 policy evaluations, 2,000 watcher
  ticks, 20 lifecycle cycles and 50 injected failures, with zero file-descriptor
  or thread leakage. A Windows-only legacy test invocation exposed console GBK
  decoding in the existing location test harness; the same test passed under
  the authoritative Linux suite and is not attributed to the kernel change.

### 2026-10-09 — Typed memory projection begins

- Implemented idempotent memory projection in the same transactional store as
  the experience journal, with explicit kind, authority, state, validity,
  sensitivity, provenance and transition history.
- A confidence-1.0 model inference remains `proposed`; only admitted authority
  can activate it. Direct observations cannot activate inferred preferences.
- Contradictory evidence contests both claims instead of overwriting either.
  An explicit user correction can supersede a live matching target, but cannot
  reuse an already superseded target to create parallel active truths.
- Retrieval now requires an explicit sensitivity clearance. Projection state
  can be discarded and deterministically rebuilt from journal history.
- Implementation review changed correction ordering: explicit supersession is
  processed before same-value deduplication so user authority is not erased by
  a prior contested observation.
- The typed-memory contracts passed repeated Windows runs and the complete
  Linux regression/matrix/scaled-stress suite, including concurrent projection,
  discard-and-rebuild replay, lifecycle rollback and failure injection. The
  kernel remains shadow-only and has not ingested production conversation data.
- The first memory prototype exposed a deliberate boundary problem: private
  values embedded in an append-only event cannot be genuinely forgotten.
  ADR-0003 therefore proposes a durable metadata journal plus a separately
  erasable content vault. Production plaintext ingestion remains blocked until
  WAL, backup and interrupted-erasure tests prove the selected design.

### 2026-10-10 — Erasable content boundary prototype

- Inspected Hermes 0.21.3's real vault implementations before choosing a
  design. The built-in Fernet login vault and interactive 1Password/Bitwarden
  backends do not provide an arbitrary, headless content-erasure contract, so
  Alive does not pretend they do.
- Added an AES-GCM content vault that stores only authenticated ciphertext and
  metadata, returns opaque journal-safe references, audits resolution, enforces
  retention deadlines and records durable tombstones.
- Erasure now survives interruption: live ciphertext deletion, WAL truncation,
  compaction and affected managed-backup purge resume on next open. Unmanaged
  disk images are explicitly outside the claim; this is an honest threat-model
  boundary rather than a promise software cannot keep.
- A Windows concurrency test found that simultaneous first-open WAL setup
  could leak a failed SQLite handle. Initialization now retries the transient
  lock and closes every failed handle. Thread/process first-use and concurrent
  backup/erase races are covered. Repeated Windows runs, Linux host, the actual
  Hermes NAS container, and the full Linux regression/matrix/stress suite
  passed.
- Production plaintext ingestion remained disabled while the next phase moved
  proposal values behind content references and defined explicit erased-state
  replay semantics.

### 2026-10-10 — Private memory leaves durable history

- Replaced persisted memory values with opaque encrypted-content references;
  neither `memory.proposed` nor `memory_records_v2` carries plaintext.
- Replaced plain value SHA-256 with an installation-keyed HMAC after threat
  review showed that cities, languages and booleans could otherwise be
  dictionary-enumerated from the journal.
- Made forgetting a durable, replayed event with exact target snapshots.
  Subject replay therefore erases only memories that existed when the user
  requested it, never later memories for the same person.
- Added one-to-many logical-memory/content associations so deduplicated
  proposals cannot leave orphaned private copies behind.
- Retrieval by ID now requires the same explicit sensitivity clearance as set
  retrieval. Missing, corrupted and erased content is typed and excluded from
  normal recall rather than fabricated.
- Repeated/concurrent append, cross-subject substitution, crash continuation,
  item/subject erasure and discard-and-rebuild pass on Windows, Linux and the
  actual Hermes Docker runtime. Production ingestion remains disabled pending
  WSL, lifecycle/doctor and operator-control gates.

### 2026-10-10 — Explainable recall baseline

- Added authorization-first memory search using BM25 and Reciprocal Rank
  Fusion over independent relevance, importance, recency and authority lists.
  This replaces a tempting but opaque hand-weighted “memory score.”
- Each result exposes matched terms, component ranks and the original source
  event IDs. A query cannot admit an unrelated memory merely because it is
  newer or marked important.
- CJK bigrams avoid the false matches produced by common single characters;
  no-match queries return silence rather than the least-bad memory.
- Semantic embeddings remain an optional future Hermes capability: private
  memory will not be silently exported to whichever model happens to be
  configured.
- Review of duplicate evidence found and fixed a privacy escalation bug: the
  logical memory now inherits the strictest sensitivity seen across equal
  claims, never the first/least restrictive label. Its primary reference also
  moves to ciphertext authenticated at that stricter sensitivity.
- Projection decisions, record timestamps and transitions now derive from the
  durable event clock rather than replay wall time. Rebuild tests compare
  timestamps as well as rankings, preventing recency drift after recovery.

### 2026-10-10 — Durable agenda baseline

- Added separate commitment and opportunity records instead of treating every
  interesting signal as a task or every task as ordinary memory (ADR-0006).
- Model and observation authorities may propose a commitment but cannot
  activate one. User-authorized transitions must cite a matching durable
  inbound event; a caller-provided authority label alone is insufficient.
- Agenda content uses the same encrypted, erasable vault boundary as memory.
  Deadlines, availability, provenance and lifecycle remain structural events.
- Snooze, completion, dismissal and expiry are distinct replayable states.
  Proposal retries are semantically idempotent despite fresh wall-clock values.
- The agenda remains shadow-only and performs no scheduling, policy decision,
  delivery or other external action.

### 2026-10-10 — Policy-bounded deliberation baseline

- Replaced the idea of one opaque “proactivity score” with independently
  evidenced value, urgency, novelty, confidence, interruption-cost, risk and
  authority assessments (ADR-0007).
- Every frame has exactly one deterministic silence candidate. Hard policy
  filters run before a model can choose, and selection is checked again after
  the model response.
- Candidate content, assessment reasons and model rationale live in the
  encrypted erasable vault. Structural journal events retain IDs, policy
  outcomes and causal links without private prose.
- Frame loading recomputes policy, verifies every cited evidence event and
  resolves every candidate content reference. Dangling evidence cannot appear
  as an auditable reason.
- Accepted and rejected selections survive discard-and-rebuild identically.
  No provider is called and no selected action is executed in this phase.

### 2026-10-10 — Evidence-backed outcome baseline

- Added an explicit action-attempt boundary between model selection and an
  external effect. Attempts carry stable idempotency keys but do not execute
  channel or tool operations themselves (ADR-0008).
- Delivery receipts, user replies/corrections/dismissals, explicit feedback and
  downstream task completion/failure require compatible source events that
  occur after the attempt and match its subject.
- `no_reply` is intentionally absent from the outcome vocabulary. Time passing
  cannot silently become rejection, negative reward or a social penalty.
- Private outcome detail is encrypted and erasable. Erasure preserves the
  structural fact and replay result while returning an explicit erased status.
- The result ledger remains shadow-only; no production delivery is attempted.

### 2026-10-10 — Reviewable reflection baseline

- Reflections are now expiring hypotheses rather than direct memory mutations
  or invisible prompt edits (ADR-0009).
- Delivery receipts and ordinary replies cannot support a reflection. Model
  synthesis requires explicit correction/dismissal/feedback or repeated task
  outcomes from independent attempts.
- Every proposal points to real outcome rows and the corresponding causal event.
  A historical user message from before the proposal cannot approve it.
- Acceptance, rejection and later retraction require matching user inbound
  evidence. Even accepted reflections do not automatically alter memory,
  thresholds or delivery policy.
- Encrypted reflection prose can be erased while its proposal/review history
  remains deterministic and visibly marked as erased.

### 2026-10-10 — Conservative preference-estimation baseline

- Kept explicit preferences in the typed-memory authority model and introduced
  a separate advisory estimator for weak learned patterns (ADR-0010).
- Only explicit feedback outcomes and currently accepted reflections can create
  learning signals. Delivery success, ordinary replies, model opinion and
  non-response cannot enter the estimator.
- Each source contributes once, per-origin weight is capped, total evidence
  mass is bounded and every signal expires. Repetition therefore cannot turn a
  weak estimate into an authoritative rule.
- Preference targets and rationale remain encrypted; only a keyed digest enters
  structural history. A stricter source can never be projected at a lower
  sensitivity.
- Retracting a reflection removes its contribution immediately. Explicit user
  retraction removes a signal, and discard-and-rebuild reproduces the result.
- Estimates are shadow-only and are not yet consumed by live deliberation.

### 2026-10-10 — Constrained exploration baseline

- Added a second gate that can only narrow candidates already admitted by the
  main authority/risk/interruption policy; it can never rescue an unsafe action
  (ADR-0011).
- Exploration count, topic share, source share and same-topic streak have
  explicit rolling limits. Silence always remains admissible when diversity
  rejects every action.
- Only successful delivery receipts enter exposure history. Selection, attempt,
  failed delivery and no-response do not pretend that the user saw an item.
- Topic and source labels are encrypted; structural history accepts only keyed
  digests, preventing accidental plaintext metadata leakage.
- Gate results are recomputed on replay and stored as causal receipts. Every
  non-silence model selection must cite an earlier receipt that admits its exact
  candidate; direct bypass is rejected.
- The mechanism remains shadow-only and has not altered production discovery
  or delivery behavior.

### 2026-10-10 — Honest held-out replay baseline

- Added time-separated evaluation of predictions made before factual action
  attempts. Training state cannot cross the holdout boundary and cited evidence
  must precede the attempted action.
- No response and missing labels remain unknown. Conflicting positive and
  negative evidence is also unknown rather than silently averaged into a
  convenient reward.
- Calibration comparisons require the exact same executed-attempt cohort.
  Reports explicitly refuse to claim that an unexecuted action or a different
  selection policy would have performed better.
- This closes the measurement primitive, not the Phase-4 exit gate: a real
  sanitized corpus and longitudinal shadow results are still required.

### 2026-10-10 — Official Hermes structural event adapter

- Verified the current Hermes hook contract from its running source before
  expanding the adapter: lifecycle/session events plus agent start, step and
  end are official; their contexts contain raw private content. The contract
  was cross-checked against upstream `main` at `f925b017` as well as the running
  Hermes Agent 0.21.3 image, rather than assuming legacy compatibility.
- Added all official non-command lifecycle and agent events to the hook while
  keeping the legacy watcher behavior unchanged. The shadow boundary stores
  only local pseudonyms, bounded structural counts and content-presence flags.
- Added persistent start/step/end causation and deterministic retry identity.
  Concurrent duplicate starts collapse to one event, while the same text sent
  again after completion becomes a new turn.
- Gateway restart and unexpected turn replacement now append a durable
  interruption fact before clearing activity state. Raw messages, assistant
  responses, model/provider aliases, tool arguments and tool results remain
  absent from SQLite/WAL evidence.
- This does not yet claim semantic message ingestion or authoritative tool
  outcomes; those remain gated on retention controls and native typed receipts.

### 2026-10-10 — Explicit erasable content consent

- Added `/memory alive` controls on Hermes' own slash authorization path. The
  hook consumes only its `alive` sub-namespace and leaves ordinary `/memory`
  behavior untouched across every Hermes channel.
- Default retention is off per pseudonymous user. Explicit consent chooses
  inbound, outbound or both, with a one-to-365-day fixed expiry. A model event
  cannot grant or widen consent.
- Authorized hook text is encrypted in the erasable vault; journal events keep
  only opaque authenticated references, the consent event and an honest marker
  that the official hook may truncate at 500 characters. Tool arguments and
  results remain forbidden.
- `retain off` stops future capture without rewriting history. `forget` is a
  durable request/execution/completion workflow that deletes subject content
  and managed backups, resumes after interruption, and works even when kernel
  shadow decision capture is disabled.
- Windows and Linux tests prove default-off behavior, per-user authorization, model
  rejection, encrypted-at-rest capture, ordinary `/memory` pass-through,
  disable-versus-forget semantics, replay and crash-resumed erasure. The real
  Hermes container also discovered `command:memory`, intercepted only `alive`
  requests and left ordinary memory commands untouched.

### 2026-10-10 — Honest native tool receipts

- Registered Alive against Hermes' public `post_tool_call` plugin hook instead
  of scraping assistant text or the lossy gateway step summary.
- Receipts contain pseudonymous call coordinates, tool name, bounded duration
  and terminal classification only. Arguments, results and error messages are
  excluded, and the observer stays inert unless kernel shadow mode is enabled.
- Hermes' ordinary `ok` and `error/tool_error` labels currently depend on
  return-value inspection. They are retained only as reported diagnostics and
  mapped to `outcome=unknown`, never to success/failure learning evidence.
- Explicit policy blocks, cancellations, timeouts and exception-backed errors
  are typed, learning-eligible terminal facts (ADR-0015).
- A clean-container run exposed that the base Hermes 0.21.3 image does not
  itself include `cryptography`. The repository now declares
  `cryptography>=50.0.2,<51` and the install/upgrade contract routes dependency
  consent through `hermes plugins install --yes-deps`; an isolated install of
  50.0.2 plus the complete container suite passed without changing production.

### 2026-10-11 — Legacy Dream retirement and consented consolidation

- Source review disproved the legacy Dream documentation: the runtime did not
  merely save a diff for review. It read raw session transcripts without the
  new retention boundary and could directly mutate `MEMORY.md`, fact state and
  voice state from model output. The engine is now an inert compatibility
  tombstone; even a stale `HERMES_DREAM_ENABLED=1` cannot reactivate it.
- Separated permission to retain conversation content from permission to learn
  from it. Both default off per pseudonymous user. Retention alone never grants
  model interpretation, and learning consent without retained evidence has
  nothing to process.
- Added consolidation candidates limited to expiring fact, preference and
  self-model hypotheses. Every cited item must be decryptable retained content
  for the same subject; structural-only, erased, missing and cross-user evidence
  is rejected.
- Model output can create only an encrypted `proposed` memory. It cannot create
  commitments, delete, supersede, activate or silently alter policy. Explicit
  `/memory alive accept|reject|retract` review is the only activation path.
- Candidate IDs and command operation IDs are semantic idempotency keys;
  retries converge and changed reuse fails. Consent and memory projections can
  be discarded and deterministically rebuilt from the journal.
- This completes the safe consolidation primitive, not autonomous production
  learning. Candidate generation is not scheduled and production remains
  unchanged pending corpus evaluation and shadow qualification.
- The complete Windows run exposed a separate packaging defect: Python's
  `zoneinfo` has no system IANA database on ordinary Windows, while the plugin
  did not declare `tzdata`. The plugin now declares it explicitly so Circadian
  behavior survives a true fresh Windows install instead of depending on a
  developer machine's incidental packages. The same clean-image run confirmed
  that YAML parsing was also an undeclared runtime assumption, so `PyYAML` is
  now part of the plugin dependency contract rather than only CI setup.
