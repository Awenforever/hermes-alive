# ADR-0002: Memory is a typed, reversible projection—not model-authored truth

- Status: accepted for Phase 2 implementation
- Date: 2026-10-09
- Revisit when: replay evaluation shows the type/authority model is too coarse

## Context

Alive 2.9.8 spreads remembered state across context snapshots, preferences,
topic history, voice state, `MEMORY.md`, facts and Dream diffs. Dream can apply
an operation after a model labels it high-confidence. This makes confidence do
the work of evidence and makes correction, contradiction and forgetting hard to
reason about.

Long-term initiative is unsafe unless Hermes can distinguish what the user
said, what the environment demonstrated, what a model inferred, what Hermes
promised, and what was merely generated as a reflection.

## Decision

Memory will be a rebuildable projection from the experience journal. Every
record has all of the following dimensions.

### Kind

- `episode`: a bounded event or interaction;
- `fact`: a claim about the world;
- `preference`: a user-stated or cautiously learned preference;
- `commitment`: an obligation, promise or expected follow-up;
- `self_model`: Hermes capability, limitation or stable presentation choice;
- `reflection`: a strategy lesson proposed from outcomes.

### Authority

- `user_explicit`: the user directly stated or corrected it;
- `direct_observation`: a capability produced structured evidence;
- `system_migration`: a traceable import from an earlier schema;
- `model_inference`: a model inferred it from evidence;
- `reflection`: a model or evaluator proposed a lesson.

Authority and confidence are separate. A model output at confidence `0.99` is
still an inference. It cannot silently replace an explicit user statement.

### State

- `proposed`: not available to ordinary behavior;
- `active`: eligible for retrieval under privacy and validity policy;
- `contested`: contradictory evidence exists;
- `superseded`: a later authorized correction replaced it;
- `retracted`: explicitly withdrawn or invalidated;
- `expired`: outside its validity period.

No row is updated in place to erase its history. State transitions cite the
event that caused them. User-facing forgetting is not implemented by a cosmetic
tombstone: sensitive payloads will require deletion/compaction or cryptographic
erasure, designed before raw conversation ingestion is allowed.

## Admission policy

1. Explicit user assertions may become active after schema validation.
2. Direct structured observations may activate episodes/facts, but conflicting
   observations become contested rather than overwriting each other.
3. Model inference and reflection remain proposed until deterministic evidence
   or an authorized review promotes them.
4. Commitments require an identifiable promisor, beneficiary, condition and
   lifecycle; prose resembling a promise is not enough.
5. Preferences learned from behavior remain weak and reversible. Silence is
   not negative preference evidence.
6. All source event IDs must exist and be retrievable under the same privacy
   authority as the memory.

## Retrieval policy

Retrieval filters authority, state, validity and sensitivity before relevance.
Ranking may then combine recency, semantic relevance and importance. A high
similarity score cannot bypass admission or privacy policy.

Retrieved values carry citations to their source events and any contradiction
or uncertainty. The composer receives those citations; it must not flatten them
into unqualified truth.

## Consequences

Positive:

- user corrections have deterministic precedence;
- hallucinated reflection cannot become durable truth by self-confidence;
- memory can be replayed, inspected and tested independently of prompts;
- commitments and preferences gain explicit lifecycle semantics.

Costs:

- more records remain proposed or contested instead of producing immediate
  personalization;
- projection and erasure migrations require careful transactional design;
- model prompts must preserve citations and uncertainty.

## Rejected approaches

- **One editable `MEMORY.md`:** simple, but loses type, provenance and conflict
  history.
- **Vector database as the source of truth:** useful as an index, not an
  authority or lifecycle model.
- **Model confidence threshold:** confidence is not evidence or permission.
- **Keep every transcript forever:** violates minimization and makes useful
  retrieval harder, not easier.
