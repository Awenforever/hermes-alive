# ADR-0003: Separate durable history from erasable private content

- Status: proposed; prototype and backup-erasure proof required
- Date: 2026-10-09
- Blocks: production ingestion of raw conversations and private memory values

## Context

ADR-0001 makes experience history append-only so decisions can be replayed and
audited. ADR-0002 requires real user correction and forgetting. Those goals
conflict if a `memory.proposed` event embeds private plaintext: changing the
memory projection or adding a tombstone does not remove the value from the
journal, WAL, copied database or backup.

The Phase-2 prototype currently exercises synthetic values in journal events.
It is not enabled in production and must not be promoted in that form.

## Proposed decision

Split persistence into two security domains.

### Durable history

The experience journal may retain:

- event type and time;
- pseudonymous subject and causal identity;
- schema, authority and policy decision;
- content digest, size class and retention class;
- delivery/outcome facts that contain no private plaintext;
- an opaque reference to erasable content.

It must not retain conversation text, credentials, attachment contents,
private memory values or reversible external identifiers.

### Erasable content vault

Private content lives behind an opaque content ID. The vault owns:

- purpose and retention deadline;
- subject and sensitivity scope;
- encryption/key or secure-deletion strategy;
- explicit access checks and access audit;
- correction, deletion and compaction;
- backup-retention coordination.

Memory projection resolves a content reference only after state, validity and
sensitivity policy admit the record. Retrieval results still cite journal
events, but the event history alone cannot reconstruct erased plaintext.

## Required proof before acceptance

1. Searching the journal, WAL and projection database never reveals a private
   sentinel before or after normal operation.
2. After erasure, the sentinel is absent from the live vault, WAL, temporary
   files and a newly created backup.
3. Existing backups either expire under a declared bounded policy or use
   envelope keys whose destruction makes the erased content unrecoverable.
4. Replay after erasure produces an explicit `content_unavailable_erased`
   state rather than fabricating, crashing or restoring the value.
5. Subject-wide and item-specific deletion are idempotent and do not delete
   unrelated users or shared public evidence.
6. Windows, Linux, WSL and Docker/NAS lifecycle tests cover file locking,
   backup, restore and interrupted erasure.

## Options under evaluation

### Physical SQLite deletion with secure compaction

Portable and dependency-free, but cannot retract copies already present in
external backups. Suitable only with a strict, visible backup retention policy.

### Envelope encryption with per-subject or per-item data keys

Cryptographic erasure can cover immutable backups by destroying keys, but only
if implemented with a maintained authenticated-encryption library and a durable
key hierarchy. We will not implement custom cryptography.

### Hermes-owned secure content capability

Preferred when Hermes exposes a stable cross-platform secrets/private-content
store. Alive should consume that capability instead of creating a competing
credential system. Current availability and lifecycle guarantees must be
verified rather than assumed.

## Immediate constraint

Until this ADR is accepted with passing evidence:

- kernel shadow events remain structural and pseudonymous;
- typed-memory tests use synthetic fixtures only;
- production conversation text is not mirrored;
- the existing 2.9.8 runtime remains the production authority.
