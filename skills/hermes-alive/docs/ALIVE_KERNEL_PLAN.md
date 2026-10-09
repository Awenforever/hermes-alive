# Hermes Alive Kernel — Living Development Plan

Status: active

Last reviewed: 2026-10-09

Current phase: Phase 1 — durable experience journal

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
- [ ] Add adapters for Hermes inbound, outbound, lifecycle and tool outcomes
  (lifecycle/session hook adapter implemented; message/tool adapters pending).
- [x] Add opt-in shadow mirroring that cannot influence legacy decisions.

Exit: restart/replay reconstructs the same ordered experience stream, duplicate
ingestion is harmless, and no secret-bearing payload crosses ingestion policy.

### Phase 2 — Typed memory and beliefs

- [x] Define memory kinds, authority classes, lifecycle states and admission
  principles; see `adr/0002-typed-memory-is-a-projection.md`.
- [ ] Implement episodic, semantic, preference, commitment and self-model
  records with provenance, confidence, validity, sensitivity and supersession.
- [ ] Retrieve by recency, relevance and importance without losing provenance.
- [ ] Make correction, forgetting and privacy erasure propagate predictably.
- [ ] Replace direct Dream mutation with reviewable memory proposals.

Exit: every retrieved memory explains why it exists; contradictions and user
corrections are represented rather than overwritten.

### Phase 3 — Agenda, intentions and deliberation

- [ ] Add durable commitments and opportunity records.
- [ ] Generate multiple candidate actions, including deliberate silence.
- [ ] Evaluate user value, urgency, novelty, confidence, interruption cost,
  risk and authority separately.
- [ ] Let the model deliberate within structured bounds; keep policy external.
- [ ] Run the new decision engine in shadow against production events.

Exit: every proposed action has a stable reason and every rejection is
inspectable; replay is deterministic outside explicitly recorded model calls.

### Phase 4 — Outcomes, reflection and learning

- [ ] Link delivery, reply, correction and downstream task outcomes to actions.
- [ ] Learn timing, topic and presentation preferences conservatively.
- [ ] Treat no reply as ambiguous, never as punishment evidence.
- [ ] Store reflections as evidence-backed proposals with expiry and rollback.
- [ ] Add constrained exploration budgets and anti-echo-chamber diversity.

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
