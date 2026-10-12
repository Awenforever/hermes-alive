# ADR-0042: Revalidate cached user outcomes on read

Status: accepted for outcome reads; dependent projection hardening pending

## Decision

An `action_outcomes_v1` row is a cache, not evidence that its original
admission still satisfies the current contract. Before returning an outcome,
load its original journal event and check cache identifiers, kind and subject
against it. For user outcomes, recheck exact attempt/source causation, event
order, observation times, actor/subject boundaries and the explicit operation
metadata required by ADR-0041.

Invalid legacy rows are excluded from returned outcomes. Do not delete their
journal events, ciphertext or projection rows merely because they no longer
qualify. A deliberate rebuild can reconstruct current valid results, but a
reader must remain safe even when nobody rebuilt the cache.

The `user_attribution_valid` helper concerns user attribution only. Its result
for non-user outcomes is not proof of transport/task causation or delivery.
Those contracts still need their own audit.

## Evidence and incomplete paths

The regression test inserts an unrelated same-user result directly into the
cache, emulating an old admitted row. Current reads exclude it while its
original journal event remains. Valid outcomes and deterministic rebuild
behavior continue to pass the existing test.

Audit also confirmed that reflection evidence and preference estimates read
materialized tables directly. This milestone does not sanitize those paths;
new proposal admission and current accepted/learned reads must both be covered
before activation. Do not declare the feedback loop safe based on this one
reader. Production is unchanged.

On 2026-10-12 outcome, reflection and preference-learning tests passed on
Windows and in an isolated production-image container without networking or
production-data mounts. Cache-to-journal checks also bind content identity,
sensitivity and observation time before resolving private details. Production
was not deployed or restarted.
