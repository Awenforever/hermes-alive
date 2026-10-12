# Hermes Alive Kernel — Living Development Plan

Status: active

Last reviewed: 2026-10-12

Current phase: Phase 5 — faculty migration in bounded shadow mode

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
  before activation (ADR-0016).
- [x] Add a provider-neutral synthesis boundary that uses Hermes model routing,
  independently validates candidates, records actual-model attribution and
  persists no raw prompt/response (ADR-0018). Automated invocation remains
  shadow/off until longitudinal quality evidence exists.

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
  encrypted, deterministic replay projection. A provider-neutral Hermes-routed
  selector now exists behind an unscheduled, non-executing boundary (ADR-0021).
- [x] Join candidate framing, active-agenda validation, exploration and a
  durable selection in one crash-safe coordinator that always closes with
  deterministic silence and has no model/channel/tool side effects (ADR-0020).
- [x] Separate selected intent from send-time authority. Short-lived structural
  permits now recheck latest state, current policy, active user authority,
  evidence and the exact Hermes capability without executing (ADR-0022).
- [x] Require every durable action attempt to consume an unexpired matching
  authorization receipt, with latest-state rechecks and dependency-ordered
  crash recovery (ADR-0023). No executor is connected.
- [x] Materialize authorized attempts into a deadline-bounded leased outbox;
  prove concurrent claim exclusion, stale-token rejection, crash recovery,
  authenticated result reconciliation and no-redelivery recovery (ADR-0024).
- [x] Replace caller-supplied execution policy with user-owned, revisioned,
  replayable autonomy state; bind authorization and dispatch to its exact
  version so pause and policy changes revoke queued work (ADR-0025).
- [x] Distinguish leased, externally started and uncertain dispatch so a crash
  at the adapter boundary can neither duplicate nor falsely claim an action.
  Terminal results bind the exact start generation, and v2 leases migrate
  conservatively to uncertainty (ADR-0026).
- [x] Replace arbitrary candidate JSON at the execution boundary with a
  versioned, destination-free action contract. Bind it cryptographically into
  authority, attempt validation and dispatch (ADR-0027).
- [x] Bind authorization and dispatch to an authenticated snapshot of actual
  Hermes host capabilities plus a separately encrypted, user-authorized route.
  Request acceptance is not delivery evidence, so the live bridge remains
  disconnected while the stable public plugin API lacks terminal delivery
  receipts (ADR-0028).
- [x] Replace per-acquisition full-history evidence scans with a rebuildable,
  transactionally checkpointed projection. Batch size bounds transaction cost,
  never history correctness; journal facts are re-authenticated on use
  (ADR-0029).
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
- [x] Define complete blinded-review metrics and a minimum qualification gate
  for memory consolidation: false-memory classes, durable-claim recall,
  citation accuracy, safe silence, duplication and review burden remain
  separate measures (ADR-0019). The checked-in corpus is synthetic machinery
  proof, not longitudinal product evidence.

Exit: learning improves held-out replay metrics without increasing interruption,
factual error or user-control violations.

### Phase 5 — Faculty migration

- [x] Port external Discovery through a typed opportunity-only ingestion
  boundary with encrypted evidence, material-update supersession and a
  dual-opt-in no-send shadow bridge (ADR-0030). Local filesystem discovery
  remains deliberately outside this completed external-source slice.
- [ ] Split user availability from optional character-like Circadian styling:
  - [x] add a replayable, fail-closed availability projection where direct
    activity can block but absence cannot grant permission (ADR-0031);
  - [x] add a dual-opt-in one-way shadow bridge from the legacy activity guard;
  - [ ] remove Circadian phase as live interruption authority after shadow
    comparison and retain it, if useful, only as presentation rhythm.
- [ ] Port voice as presentation policy, not a truth source:
  - [x] add a replayable explicit-preference projection with deterministic
    neutral defaults and advisory-only inferred/legacy state (ADR-0032);
  - [x] add a dual-opt-in one-way legacy voice shadow bridge;
  - [x] add encrypted meaning atoms, a provably lossless deterministic
    renderer and fail-closed classification for free model output (ADR-0034);
  - [x] define an independent semantic-review contract, explicit failure
    taxonomy and complete multilingual adversarial replay metrics (ADR-0035);
  - [ ] build a qualification-sized human-calibrated corpus and user
    inspect/correct controls;
  - [ ] replace the legacy live voice consumer only after shadow qualification.
- [ ] Replace heuristic mood with explainable dispositions:
  - [x] define authenticated post-selection expression cues that retain each
    independent dimension's evidence and grant no decision authority
    (ADR-0033);
  - [x] add the meaning-first deterministic fidelity baseline (ADR-0034);
  - [x] persist encrypted model candidates and authenticated review receipts
    with selection/erasure/expiry invalidation (ADR-0036);
  - [ ] connect a provider-neutral model-rendering shadow comparator to the
    ADR-0035/0036 contracts;
  - [ ] remove legacy mood, relationship and `social_urge` influence only
    after replay and canary qualification.
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

### 2026-10-12 — Revalidated semantic-review receipts

- Added encrypted persistence for free model candidates; the journal retains
  only a content reference, digest, renderer provenance, changed atom IDs and
  explicit authority nonclaims (ADR-0036).
- Added authenticated structural review receipts bound to the exact candidate
  event, selection, reviewer execution/model/domain and complete atom findings.
- Every read now decrypts and re-hashes content, reruns deterministic and
  independent checks, confirms the bound selection is still latest and checks
  current expiry. A signature alone is deliberately insufficient.
- Verified fail-closed invalidation after superseding intent, candidate erasure,
  renderer-evidence mismatch and expiry. Raw candidate text and review prose
  never enter the experience journal.
- The store remains shadow-only and performs no provider call or delivery.

### 2026-10-12 — Independent semantic review and adversarial replay

- Corrected an over-conservative baseline: ordinary paraphrases now require
  review instead of failing merely because they do not contain the entire
  source sentence. Missing protected dates, amounts, links, contacts,
  negation or uncertainty markers still fails closed.
- Added an exact candidate-digest review contract with complete per-atom,
  added-claim, speech-act and protected-literal findings (ADR-0035).
- Required distinct renderer/reviewer executions, actual model identities and
  declared independence domains. Self-review is invalid, not weak evidence.
- Kept a clean independent result shadow-only: it grants no truth, action,
  route or delivery authority.
- Added complete-cohort metrics and a 12-case Chinese/English/Japanese
  adversarial seed covering faithful paraphrases plus nine distinct semantic
  failure classes. The seed is explicitly machinery proof, not product
  qualification; at least 100 blinded, human-calibrated cases remain required.

### 2026-10-12 — Presentation policy boundary

- Audited the legacy voice path and found that it combined prose style with
  guessed relationship stage, ignored-message counters and `social_urge`.
  Ordinary replies, silence, night activity and lexical heuristics could
  durably mutate the same state consumed by composition.
- Added an authenticated, replayable presentation projection (ADR-0032).
  Only causally proven explicit user preferences affect its resolved plan;
  accepted-learning and legacy signals remain expiring advisory evidence.
- Added deterministic neutral defaults and fail-neutral corruption behavior.
  The plan cannot grant action/route authority or permit semantic changes.
- Added a dual-opt-in one-way legacy bridge. It stores pseudonymous subjects
  and numeric dimensions only, and the production watcher never reads back
  the shadow result.
- Current research/product evidence supports separating controllable style
  from capability and safety, while warning that implicit personalization can
  change safety and utility. This strengthens the requirement for explicit
  provenance and independent semantic-fidelity evaluation.

### 2026-10-12 — Explainable post-selection disposition

- Audited the legacy proactive disposition and confirmed it blends synthetic
  mood, relationship stage, social urge, non-response and personality into an
  opaque willingness score before the send decision.
- Reframed disposition as expression after a selection is independently
  validated (ADR-0033). Risk, interruption cost, urgency and grounded novelty
  produce separate evidence-carrying cues; there is no blended mood score.
- Silence and non-communication actions produce no renderable disposition.
  Every snapshot denies emotion/relationship claims, action authority,
  selection mutation and semantic change.
- Consumers must re-authenticate and recompute the snapshot from the latest
  validated selection. The new path is unscheduled and not connected to the
  production watcher.

### 2026-10-12 — Meaning-first semantic fidelity baseline

- Added encrypted, evidence-linked semantic atoms before style rendering
  (ADR-0034). Critical dates, amounts, links, contacts, uncertainty and
  negation require exact protected literals.
- Bound meaning to a strict reference-only deliberation candidate and then to
  the exact latest validated selection. A later validated intent invalidates
  the old render receipt even if the candidate identity is unchanged.
- Added a deterministic renderer that changes separators only and can prove
  exact transformation fidelity. It stores raw text only in the erasable
  content vault.
- Free model output cannot self-certify. Missing atoms/literals are rejected;
  otherwise it remains `review_required` because extra prose can introduce
  unsupported claims or shift relations.
- Clarified the proof boundary in code and events: rendering fidelity does not
  prove truth, evidence entailment, action authority or route authority.

### 2026-10-12 — Incremental dispatch evidence projection

- Removed the full-journal reverse scans from every outbox reconciliation and
  acquisition path.
- Added an atomic checkpoint plus a minimal index of authenticated start/result
  event identities. Projection runs to a captured watermark in bounded batches
  rather than applying a correctness-breaking look-back limit.
- Added concurrent projector, invalid-authenticator, incremental catch-up and
  discard-and-rebuild tests. Derived rows are installation-authenticated and a
  startup count/HMAC audit rebuilds logical corruption before leasing. Startup
  recovery reports evidence checkpoint progress before materializing dispatch
  state.

### 2026-10-11 — Host capability and route authority boundary

- Audited official Hermes `v0.21.6` at `f27cdbce`: the public plugin injection
  API schedules a turn but explicitly does not prove completion; adapter
  `SendResult` and the final-delivery ledger remain internal to the gateway.
- Added authenticated, versioned host capability snapshots with explicit
  receipt semantics. A private API or request-accepted-only interface cannot
  authorize proactive external delivery.
- Added encrypted route bindings requiring exact user authority. Journal state
  retains only structural references and a keyed route fingerprint; route
  plaintext stays in the erasable vault.
- Bound send-time authorization and dispatch start to the exact route and host
  snapshot. Host upgrades, route revocation, content erasure and receipt-level
  downgrade fail closed before external start.
- Kept production `v0.21.3` and the legacy watcher untouched. The new live
  bridge remains deliberately absent until a supported terminal-receipt API
  exists.

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
- A clean-container run initially used the system Python instead of Hermes'
  virtual environment and incorrectly concluded that cryptography was absent.
  The supported Hermes environment actually locks `cryptography==50.0.0` and
  already provides AES-GCM. A later isolated dependency-resolution run caught
  that the resulting `>=50.0.2` declaration would force a host conflict. The
  plugin now matches the Hermes lock and still routes dependency consent
  through `hermes plugins install --yes-deps`.

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

### 2026-10-11 — Ordered crash recovery supervisor

- Added one startup recovery boundary for every implemented kernel projection
  instead of relying on whichever command or subsystem happens to run next.
- Recovery resumes erasure/expiry first, then advances consent, memory, agenda,
  deliberation, outcomes, reflection, preference and exploration in explicit
  dependency order (ADR-0017).
- Checkpoints advance in bounded batches and no-progress is a hard diagnostic.
  Repeated startup is a no-op after convergence; an interrupted run resumes
  from each projection's durable checkpoint.
- The supervisor is cross-process locked, creates no kernel store on a fresh
  install and has no channel, provider or tool side effects. Kernel recovery
  failure remains observable without preventing the legacy watcher startup.

### 2026-10-11 — Review-only model synthesis boundary

- Replaced the missing link between retained evidence and reviewable memory
  with a provider-neutral synthesizer rather than reviving Dream.
- Synthesis requires both retention and learning consent, consumes a bounded
  decryptable evidence window and delegates provider/fallback selection to
  Hermes' auxiliary model route.
- Strict JSON is only an interchange boundary: every candidate is validated
  independently, tied to in-window evidence and admitted solely as an
  encrypted, expiring proposal. Invalid siblings do not cancel valid ones.
- Actual response-model attribution is mandatory. Structural receipts contain
  no raw prompt, response or provider error text, and repeated operation IDs
  cannot trigger another model call.
- The callable remains unscheduled and cannot affect production behavior. The
  next evidence gate is a sanitized historical replay corpus with
  longitudinal usefulness, false-memory and review-burden metrics.

### 2026-10-11 — Honest consolidation evaluation gate

- Added complete blinded-review accounting instead of treating strict JSON as
  a quality signal. Every candidate and every zero-candidate case must be
  reviewed; incomplete cohorts are rejected.
- Durable claims have explicit case-local IDs. An acceptable candidate must
  match one ID and a claim cannot be counted twice, so recall cannot be entered
  as an unsupported aggregate number.
- Precision, recall, citation accuracy, sensitive/authority failures,
  duplication, safe silence and review burden are reported independently.
- A ten-case multilingual synthetic seed exercises the evaluator without
  containing historical user data. It explicitly does not close the Phase-0
  sanitized historical corpus or longitudinal evidence gates.

### 2026-10-11 — Subject authority boundary audit

- Pre-coordinator review found that agenda proposal sources were checked for
  existence but not subject ownership, and a caller-provided
  `USER_EXPLICIT` label could activate a commitment without proving the caller
  was that user. Proposal admission now proves both source scope and authority.
- Durable deliberation frames now reject foreign-subject evidence and reject
  missing, inactive or foreign agenda references. A valid active agenda item
  for the same subject is covered by an integration contract.
- This safety correction precedes the unified cognition-cycle coordinator;
  connecting components before fixing identity boundaries would have amplified
  the defect across the full action chain.

### 2026-10-11 — Integrated safe-silence cognition cycle

- Added a deterministic coordinator joining candidate frames, active agenda
  references, diversity annotations, the exploration gate and a durable
  selection in one idempotent cycle (ADR-0020).
- The coordinator deliberately selects silence even when an external action is
  admissible. This proves crash recovery, replay and audit structure without
  quietly turning integration work into production autonomy.
- Same-semantics retries add no journal events. Changed reuse fails closed, raw
  candidate content and diversity labels remain outside the structural SQLite
  history, and projection rebuild reconstructs the same gate and selection.

### 2026-10-11 — Gated provider-neutral intent selection

- Added an unscheduled selector that consumes only candidates admitted by both
  deterministic policy and the replayed exploration gate (ADR-0021).
- Provider choice and fallback remain Hermes responsibilities; receipts record
  the actual responding model, not the requested alias.
- Invalid JSON and forbidden IDs are contained before durable selection. Raw
  prompts, responses, rationales and provider errors do not enter the
  structural journal.
- A validated model choice still creates no action attempt and performs no
  channel/tool side effect. Replay and production shadow evidence remain
  required before it may be invoked automatically.

### 2026-10-11 — Short-lived send-time authority

- Added a non-executing authorizer between validated model intent and any
  future action attempt (ADR-0022).
- The boundary rechecks the latest selection and exploration gate, active
  agenda, current interruption/risk policy, evidence lifetime, subject,
  sensitivity and exact Hermes capability.
- Tightened authority provenance: an observed opportunity is not delegation,
  and an unrelated inbound message cannot be treated as confirmation.
- Authorized receipts expire within 60 seconds and are not revived by an
  idempotent retry. No production sender consumes these receipts yet.

### 2026-10-11 — Authorized attempts and causal recovery

- Removed the supported direct path from validated selection to action attempt;
  attempts now consume an exact, live ADR-0022 receipt (ADR-0023).
- Attempt projection independently rejects missing, expired, capability-
  mismatched and superseded authorization before any executor can act.
- Split recovery into deliberation-frame, exploration, deliberation-selection
  and outcome phases so empty projections reconstruct causal state in the same
  order as online admission.

### 2026-10-11 — Leased dispatch outbox

- Added a persistent outbox derived from authorized attempts (ADR-0024).
- Claims are transactional, generation-bound and short-lived; only the current
  holder can decrypt candidate content, release or acknowledge the row.
- Worker identity is pseudonymous and raw lease tokens never enter SQLite,
  journal events or logs.
- Authenticated terminal result events close the row and reconcile into normal
  outcome evidence. Losing the outbox after a successful transport cannot
  cause redelivery because reconstruction recognizes the signed result first.

### 2026-10-11 — Durable user autonomy policy

- Replaced ephemeral caller policy at authorization time with an authenticated,
  user-owned and revisioned projection (ADR-0025). No policy means disabled.
- Authorization, attempt admission and dispatch now retain the exact policy
  event. A newer policy or pause revokes pending and leased work; resuming never
  resurrects it.
- Concurrent same-revision updates select the earliest authenticated journal
  event, making online projection agree with deterministic replay.
- Review exposed the next required boundary: once a transport call begins, a
  pause cannot honestly recall it. Live adapters remain forbidden until a
  durable started/uncertain protocol closes that crash window.

### 2026-10-11 — Durable external-start boundary

- Added explicit `started` and `uncertain` dispatch states (ADR-0026).
- Candidate plaintext now crosses toward an adapter only through a one-shot
  execution grant after an authenticated structural start event is durable.
- Recovery and table-loss reconstruction never turn started work back into
  pending work. A valid late result bound to the start event and lease
  generation resolves uncertainty and projects the factual outcome.
- Added a conservative v2-to-v3 migration: an old leased row becomes uncertain
  and loses its worker/token fields rather than risking duplicate execution.
- The live Hermes capability bridge remains disconnected pending its own
  contract and provider/channel substitution tests.

### 2026-10-11 — Typed action contract and upstream capability audit

- Audited current upstream Hermes main rather than designing against the old
  production image. Public plugin injection proves request acceptance only;
  direct runner/adapter access is not a supported plugin boundary.
- Added a strict `hermes.channel.send` v1 document containing only bounded text
  and `plain|markdown` presentation. Any route, recipient, profile, thread,
  adapter or unknown field fails closed.
- Send-time authorization now binds an installation-keyed canonical action
  authenticator. Attempt and dispatch boundaries independently revalidate it
  before plaintext can cross.
- Deliberately left tool execution, internal review and live delivery
  disconnected until each has a real schema and trustworthy host receipt.
