# ADR-0003: Separate durable history from erasable private content

- Status: accepted for kernel prototyping; production integration still blocked
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

## Decision

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

The first implementation uses AES-256-GCM from Hermes' pinned
`cryptography` dependency, one random nonce per object, and authenticated
metadata binding the ciphertext to its content ID, pseudonymous subject,
purpose, sensitivity and creation time. SQLite stores ciphertext and
non-secret metadata only. The key is a profile-local mode-0600 file, matching
Hermes' current local-vault operational posture.

Erasure is a resumable workflow rather than a best-effort `DELETE`:

1. write a durable erasure job and item tombstones;
2. delete selected ciphertext in the same transaction;
3. checkpoint/truncate WAL and run secure compaction;
4. delete every affected backup inside the managed backup root;
5. mark backup purge complete.

Opening the vault resumes unfinished jobs before accepting a new managed
backup. A tombstoned content ID cannot be reused. Item and subject operations
are idempotent and keep unrelated subjects intact.

### Honest backup boundary

A self-contained backup necessarily carries enough key material to restore
its ciphertext. Consequently, deleting a live row cannot magically erase an
arbitrary old disk image or a copy the user placed elsewhere. The portable
default therefore makes a narrower, testable promise:

- Alive-created *managed backups* participate in erasure and affected older
  snapshots are removed before the job completes;
- post-erasure backups cannot reconstruct the deleted object;
- unmanaged copies and whole-volume snapshots remain governed by the
  operator's retention system and must never be described as remotely erased.

An external KMS-backed key custodian could strengthen this boundary later,
but cannot be the portable default for Windows, WSL, Linux and NAS/Docker.

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

## Alternatives evaluated

### Physical SQLite deletion with secure compaction

Portable and dependency-free, but cannot retract copies already present in
external backups. Suitable only with a strict, visible backup retention policy.

### Envelope encryption with per-subject or per-item data keys

Cryptographic erasure can cover immutable backups by destroying keys, but only
if implemented with a maintained authenticated-encryption library and a durable
key hierarchy. We will not implement custom cryptography.

### Hermes-owned secure content capability

Hermes 0.21.3 does not expose a general private-content capability. Its local
vault encrypts the complete login store with one Fernet key beside the vault
file; deleting a login rewrites current state but cannot coordinate old
backups. Its 1Password and Bitwarden backends expose login metadata and
password resolution only, and may be locked in unattended gateway/cron
contexts. Reusing those APIs would couple memory availability to interactive
login-vault semantics without solving erasure.

Alive therefore owns this narrow content primitive while consuming Hermes'
maintained cryptographic dependency. If Hermes later publishes a stable,
headless, arbitrary-content store with equivalent erasure and backup
contracts, this decision should be revisited.

## Evidence recorded 2026-10-10

- Windows: ten consecutive full contract runs passed using the same
  `cryptography==50.0.0` version pinned by Hermes. The first concurrency run
  exposed a real WAL initialization/handle leak; bounded retry and guaranteed
  close fixed it. Sixty-four concurrent thread writes and sixteen independent
  first-use processes now preserve all records. Backup/erase races are also
  serialized so no committed snapshot can escape the erasure ledger.
- Linux host: encryption, restore, interruption recovery, item/subject
  erasure, retention expiry and backup purge passed.
- NAS/Docker: the same contract passed inside the actual Hermes 0.21.3 gateway
  container with `cryptography 50.0.0`.
- The complete existing Hermes Alive Linux regression, 23-case matrix and
  scaled stress suite passed with the new vault test in the authoritative
  runner.

Still required before production plaintext ingestion: wire memory events to
content references, prove journal/projection replay after erasure, exercise a
real WSL filesystem lifecycle, and integrate managed backups with the plugin
lifecycle/doctor surface.

## Immediate constraint

Until this ADR is accepted with passing evidence:

- kernel shadow events remain structural and pseudonymous;
- typed-memory tests use synthetic fixtures only;
- production conversation text is not mirrored;
- the existing 2.9.8 runtime remains the production authority.
