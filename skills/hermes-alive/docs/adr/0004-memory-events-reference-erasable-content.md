# ADR-0004: Memory history references erasable content

- Status: accepted for kernel shadow development
- Date: 2026-10-10
- Depends on: ADR-0002, ADR-0003
- Blocks: production plaintext ingestion until lifecycle and migration gates pass

## Context

The first typed-memory prototype placed `value` in both the append-only
`memory.proposed` event and the derived `memory_records` table. Tombstoning a
row could hide it from retrieval but could never forget the value: replay or a
copied journal would restore it. A plain SHA-256 digest would not solve the
problem because low-entropy values such as a city, language or boolean
preference are enumerable offline.

## Decision

`MemoryProposal` is a transient in-process object. At the persistence boundary:

1. its JSON value is encrypted by the content vault;
2. the event receives an opaque content ID, size, retention deadline and an
   installation-keyed HMAC digest;
3. the event and memory projection never store the value;
4. projection stores the content reference and resolves it only after state,
   validity and sensitivity clearance checks.

The HMAC digest supports installation-local equality and contradiction checks
without exposing a reusable plaintext fingerprint. Vault resolution also
binds the content ID to the expected pseudonymous subject, memory kind and
sensitivity, preventing one subject's reference from being replayed under
another subject.

`MemoryProjection.get` and set retrieval both require explicit sensitivity
clearance. Unavailable content has a typed state (`erased`, `missing` or
`integrity_error`); ordinary retrieval excludes it, while inspection can ask
to include it. No caller receives a fabricated value.

## Forgetting and replay

Forgetting is itself a durable event. An item event records the exact memory
and opaque content IDs selected at that time. A subject event records an exact
target set rather than only the subject name. This matters during replay: a
subject-wide request made on Monday must not erase a new memory created on
Tuesday merely because replay happens on Wednesday.

One logical memory may have several encrypted content objects because
equal-valued proposals deduplicate into one projection while retaining their
own evidence. `memory_contents_v2` records every association, and forgetting
erases the full set. The event then transitions the projection to
`retracted`. If a crash occurs between event append, ciphertext erasure and
projection transition, replay resumes those idempotent steps.

Rebuilding after erasure processes the original proposal as metadata, then
the later forgetting event. The final record is `retracted` with
`content_status=erased` and `value=None`; history remains explainable but
cannot regenerate plaintext.

## Idempotency and schema boundary

Proposal content IDs and proposal event IDs derive from the proposal ID.
Retries converge even when a crash lands between content persistence and
journal append. Semantic retry comparison ignores newly generated observation
timestamps but rejects reuse of an ID for different content or authority.
Concurrent append races re-read and verify the winning event.

The safe projection uses `typed-memory-v2` tables and checkpoint. The content
vault schema is version 2. Pre-release schema-1 stores are rejected rather
than silently interpreting ordinary SHA digests as keyed digests. This kernel
has never been production-enabled, so there is no production private-content
migration to preserve.

## Evidence

- journal and projection files do not contain a multilingual private sentinel;
- event payloads contain `content`, never `value`;
- low-entropy content identity differs from plain SHA-256;
- cross-subject reference substitution is rejected;
- repeated and concurrent proposal append is idempotent;
- duplicate proposal content is fully erased with its logical memory;
- item and subject forgetting survive rebuild;
- post-forgetting memories for the same subject survive replay;
- unavailable content is invisible to ordinary retrieval but explicit during
  authorized inspection;
- Windows, Linux host and the actual Hermes 0.21.3 Docker runtime pass the
  content-vault and memory contracts.

## Remaining gates

- exercise the same lifecycle on a real WSL filesystem;
- add installer/doctor/backup integration and migration refusal diagnostics;
- add operator-facing inspect/correct/forget controls;
- complete sanitized longitudinal replay before any live plaintext canary.
