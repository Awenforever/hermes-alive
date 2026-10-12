# ADR-0051: Receipt aliases are not additional observations

Status: accepted for shadow admission and dependent reads; canonical election
superseded by ADR-0052's journal-based fence

## Decision

Transport/task observations identify an exact attempt, result kind and signed
dispatch start (which binds generation). Copying the signed receipt under a
different source-event ID does not create another outcome. The earliest valid
materialized observation by journal sequence is canonical. Different kinds,
starts/generations and real user source events are not collapsed by text or
similarity. User observations retain exact inbound source-event identity.

New admission records aliases as deduplicated without deleting their journal
events. Legacy cached aliases are excluded by a shared read predicate that
rechecks original evidence, complete row/reference bindings and canonical
identity. Reflections, preference sources and exposure history consume this
predicate; signature validity alone cannot multiply learning observations.

Exposure history counts the requested number of valid canonical observations,
not a SQL limit taken before validation. Newest invalid or duplicate cache rows
must not hide genuine older exposure and falsely loosen novelty constraints.

## Evidence

Signed receipt-alias integration tests prove new admission deduplicates and
directly injected old cache aliases disappear from current outcome reads and
rebuilds without erasing the journal. Erased original content remains erased,
not replaced by the duplicate's plaintext. Distinct user inbound events remain
separate even with matching classification and attempt.

Exposure regressions inject a signed alias and unsigned newest legacy row:
limit=1 still returns the original valid exposure, and exploration gating/replay
uses only that canonical evidence. Reflection tests reject alias-backed
proposals and exclude an accepted reflection when its cached evidence is
contaminated with an alias; restoring the fixture restores the valid read.

On 2026-10-12 the full Windows kernel set reported 35 passed, one official
runtime test skipped and zero failed. Updated outcomes plus reflection,
preference, exploration, evaluation and recovery tests passed in a disposable
NAS/Linux Docker image, with networking disabled and only read-only test source
mounted. These six tests do not qualify the latest Hermes package install or
replace the pending human/live quality gate.

## Limits

Canonical election still depends on the materialized observation set. Arbitrary
cache deletion/reordering beyond original-row binding, full projection repair
and large-history performance need separate audits before activation. This is
not effect deduplication at an external service, nor a decision that conflicting
terminal results or multiple dispatch generations imply a single success.
Operational reconciliation clock semantics and actual live outcome usefulness
also remain open. All changes are on the shadow branch; production unchanged.
