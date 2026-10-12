# ADR-0052: Canonical observations survive projection loss

Status: accepted for shadow admission and dependent reads

## Decision

The experience journal, not the current cache membership, determines the first
structurally valid observation for an attempt/kind/signed-dispatch-start identity.
This supersedes ADR-0051's materialized-set election. Deleting the original cache
row must not promote a copied receipt into new evidence, resurrect erased content
from its copy, or multiply learning observations.

Canonical election checks original signed/user evidence, the outcome namespace,
subject and sensitivity bindings, and the content-reference structure. It does
not decrypt content to elect identity. A well-formed original remains a fence
when its content is erased or unavailable. An invalid reference does not create
that fence. Admission applies these envelope checks as well as its existing
causal and content checks. Different actual user events and dispatch generations
retain their separate identities.

Exploration exposure reads start from journal delivery observations, rather than
assuming an empty cache means no history. Missing canonical rows, a missing
outcome table with known deliveries, or absent exposure provenance require repair
and fail closed. Aliases and unsigned observations remain excluded. Valid-history
limits still apply after evidence filtering. This is a safety decision, not a new
permission for automatic delivery or automatic database repair.

An additive partial expression index covers subject, attempt, kind and journal
sequence for outcome identity lookup. It avoids scanning unrelated events for
each election; no existing event or private production state is rewritten.

## Evidence

Synthetic regressions on 2026-10-12 demonstrate that deleting the canonical
outcome cache row cannot make a copied receipt readable. Rebuilding restores
the original outcome, with erased content still erased. A malformed earlier
reference does not poison later valid admission. Query-plan inspection selects
the new identity index.

Exposure tests remove all outcome rows, temporarily hide the entire outcome
table, and remove an annotation. Each known-history gap raises a repair-required
error rather than loosening novelty constraints. Restoring the synthetic cache
restores the expected gate and replay result. These tests touch temporary fixture
databases only; the original events remain in their journals.

The Windows kernel set reported 35 passed, one missing-runtime skip and zero
failed; the expanded exposure test passed again after adding whole-table and
provenance-loss cases. Outcomes, exploration store, reflection, preference
learning, evaluation, recovery and journal tests passed in disposable NAS/Linux
Docker with networking disabled and only read-only test source mounted. This is
not evidence of a successful latest-Hermes installation or live product quality.

## Limits and next gates

Unavailable original content deliberately remains unknown rather than silently
replaced by an alias. Full admission/rebuild equivalence under arbitrary damage,
projection repair ordering, mutated non-null provenance values, mirrored journal
column tampering and large-history performance remain unqualified. The index is
not a proof of performance at production scale. Conflicting terminal results,
external-service effect identity and reconciliation clocks remain separate work.

Human-calibrated historical/live usefulness, latest-Hermes package installation,
upgrade/uninstall/reinstall matrices, migration and rollback remain required
before activating the new kernel. All changes remain on the shadow branch;
production has not been changed.
