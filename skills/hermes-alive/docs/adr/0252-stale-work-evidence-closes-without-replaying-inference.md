# ADR 0252 — Discard stale work judgments without replaying their operation

Status: implementation candidate under isolated qualification.
Date: 2026-10-27. Extends ADR0251; no production acceptance.

A Core inspection may finish while Native is interpreting an earlier observation.
The earlier model result must be discarded, but that normal change must not poison
the durable owner cycle. The r165 actual-Core concurrent fixture confirmed that
the evidence comparison rejected the result, then a later wake reused the failed
synthesis operation and could not recover. Preserve that failed qualification.
Real-model r161/r163 also failed during interpretation, but their diagnostics do
not establish this exact cause. Do not retroactively classify them as passes.

Use a typed `OpportunityEvidenceChanged` only for the existing pre-effect
opportunity/current-commitment comparisons. Preserve a structural failed-synthesis
receipt and propagate this type. The host closes the old cycle with
`evidence_changed`, without a candidate, preparation, send or task completion.
The existing continuous loop waits its normal interval and opens a new operation
from current authority/evidence. No immediate repair loop, new scheduler or
replacement Core job is introduced. The old read-only reconciliation cursor may
be observed again; durable job and outbound identities are retained.

Authorization changes, malformed state, provider errors, invalid model output,
unknown external effects and unrelated exceptions retain their failure behavior.
This is not a generic exception-to-success conversion. In particular, an ended
Core job is not success, and a new judgment cannot repeat an inspection leaf.

Qualify with an actual Core inspector completing inside the controlled model
wait: reject the earlier answer, close the old cycle, obtain the new read result
in a later judgment, keep exactly two jobs and preserve the original producer.
Verify the continuous host remains alive after this disposition while ordinary
failures and pauses still stop it. Real inherited-model inspection and complete
regression remain separate gates.
