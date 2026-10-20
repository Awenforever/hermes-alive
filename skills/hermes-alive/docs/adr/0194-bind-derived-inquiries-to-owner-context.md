# ADR0194 — Derived reading rationale must honor owner-context withdrawal

Status: implementation and focused qualification in progress

## Reproduced defect

Reading tasks preserve a question and value hypothesis. Actual model rationale
can refer to the owner's interests, but the original task bound only its public
source observations. A negative regression with real encrypted memory/agenda
reproduced: forget an explicit preference, then the old derived rationale remains
readable for a new interpretation. Invalidating only previously completed
interpretations is insufficient; a new operation could reuse the old task.

## Decision

Discovery-inquiry-v2 records the exact bounded explicit owner-context revision
used for the reading choice. The host must capture expected_context_digest before
the model call; remember refuses a changed revision instead of rebinding a stale
model response to today's context. The encrypted task contains its binding and
the existing agenda correlation field carries a revision hash, not owner text.
Read checks this binding before agenda content decryption and before another
host read or model prompt. Typed memory stays in its own explicitly selected
vault, including custom-vault profiles; no implicit relocation or private-memory
discovery. A model task never becomes a user preference, fact or permission.

Changed or forgotten owner context requires reconsideration with a new task
identity. An identical statement supplied later has different source provenance
and cannot revive an old task. Unbound experimental-v1 tasks are retained but
refused, never silently attached to present context. This is a prototype data
validity restriction, not support for old Hermes or deletion of owner data.

## Verification and limits

Regression covers forgotten preference -> old task refusal -> new interpretation
and new host read refused before external calls; other-owner changes do not revoke
this owner; stale choice admission is refused; identical new words do not revive
the old task; default and custom memory vaults; unbound prototype refusal. Existing
task/source erasure, host-read, synthesis and recovery checks remain.

This prevents reuse at the qualified boundaries. It is NOT proof of physically
erasing every derivative ciphertext, all backups or external Halo memory; that
full retention/erasure/migration audit remains in the original goal. Encrypted
historical records are not deleted to fabricate a clean migration.

The ongoing real public-source trial stays on its original immutable archive;
do not mutate inputs or restart it to obtain a passing result. Canonical/full
qualification is pending at writing. Production unchanged; ten fresh complete
clean rounds, installed autonomous source selection, useful feedback/learning,
external memory and production acceptance remain uncompleted.
