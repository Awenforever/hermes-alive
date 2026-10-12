# ADR-0048: Evaluation labels must come from the factual snapshot

Status: accepted for shadow evaluation

## Decision

Evaluation requires an outcome projection belonging to the supplied journal,
explicit privacy clearance and optional sequence/clock snapshot bounds. It
rebuilds factual episodes through validated outcome reads and compares every
submitted episode with that snapshot before scoring. Labels, complete outcome
references, frame, candidate, attempt sequence and timestamp must all match.
Duplicate episodes, altered labels, missing/foreign/duplicated references and
silent omission of later observations are rejected, not silently repaired.

Historical evaluation remains supported by explicitly declaring the original
sequence/clock boundary. Reusing old episode labels after feedback erasure is
not supported: erased plaintext can no longer supply satisfaction labels.
Operational receipts still describe delivery even after feedback is erased.
Boolean labels are strictly bool-or-unknown; integers/strings are not coerced.

Reports carry a deterministic digest of their scored attempt metadata, full
outcome reference sets and labels. Comparison requires matching factual label
snapshots as well as matching attempt cohorts. This digest is a compatibility
check, not a signature or a claim about action-policy superiority.

## Evidence

The previous scoring test used hand-written episodes backed only by partial
attempt metadata. It has been replaced with complete admitted deliberation,
exploration, authorization, attempt, authenticated dispatch and explicitly
attributed user-feedback fixtures. Mathematical label unit tests remain clearly
separate from factual evaluation admission.

Regressions cover forged labels/frame, omitted/swapped/missing/duplicated
outcome references, duplicated episodes, explicit historical snapshots versus
undeclared stale labels, erased feedback and incompatible report snapshots.
Existing prediction-future-evidence, training holdout and cohort tests remain.

On 2026-10-12 evaluation, outcome and crash-recovery regressions passed on
Windows and in an isolated NAS/Linux Docker container with networking disabled
and only a read-only source mount. Production remained running with unchanged
start time; no production data mount or channel/model calls were used.

## Limits

This remains synthetic shadow verification. A validated projection is not
evidence of actual human satisfaction or live production behavior. Remaining
attempt/derived-cache integrity, duplicate receipt treatment, host-clock
reconciliation, human calibration and live longitudinal qualification remain
open. No production changes, feedback resurrection or outbound messages occur.
