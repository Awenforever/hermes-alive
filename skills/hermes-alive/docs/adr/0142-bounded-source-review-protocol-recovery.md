# ADR 0142 — Recover a malformed review without guessing its verdict

Date: 2026-10-15. Status: isolated implementation and synthetic qualification;
not a production deployment or successful real-model full chain.

## Problem

ADR 0141's actual model returned `unsupported` with no unsupported claims, but
nonempty uncertainties. Rejecting that contradiction was correct. Aborting every
otherwise useful cycle on a single malformed review is not a useful final design;
normalizing fields in code would instead turn guesses into semantic approval.

## Decision

The reviewer exposes an explicit `protocol_recovery` boolean, false by default.
Planning opts into at most one recovery within the same active review operation.
Only an invalid findings protocol qualifies. Network/provider errors, unknown
model family, loss of independence and stale evidence do not trigger this retry.
Valid unsupported/uncertain findings remain substantive results, not a reason to
keep asking until supported. Existing per-candidate failure isolation remains.

The invalid first response and original snapshot are retained in the encrypted
content vault with the candidate retention bound. The journal records a recovery
event with content reference, actual model/provider/domain and method digest, not
raw output. Its unique identity must be acquired before the second inference.
The second request provides original evidence and the invalid review explicitly
as untrusted data; the system instructs fresh assessment rather than approval.

Snapshot currency, generator domain and actual reviewer independence are checked
around model awaits. Context withdrawal invalidates the run. A second invalid
result stays failed. Cancellation leaves an attempted operation; reopening never
resumes or repeats inference implicitly. No old failed operation becomes success.
No provider configuration or fallback policy changes.

Recovery completion binds the exact successful raw response as encrypted content.
Reopening a recovered review also requires the original invalid evidence, matching
snapshot/method and a reparsable final response. Erasing the quarantine invalidates
the review instead of silently dropping its lineage. This does not implement
general physical cascade erasure of all derived copies or backups.

## Evidence and limits

`run_source_review_recovery.py` passes on Windows and resource-limited, read-only,
network-disabled Linux. Ten synthetic modes cover supported, unsupported and
uncertain correction; a second contradiction; disabled recovery; provider error;
lost reviewer independence; source erasure during inference; quarantine erasure;
and cancellation. Provider call counts prove one or two calls as appropriate and
zero extra calls after reopening; no action attempt or channel send is made.

The first Windows run exposed a fixture missing actual provider metadata; the
second exposed an overly narrow expected-error list for source erasure. Both
fixtures were corrected without weakening runtime behavior or assertions.

Linux adjacent literal-feedback, context synthesis, action/expression history and
final preparation/repair modes also pass. These are retained-module overlays,
not fresh installs, full portable CI or model utility/entailment evidence.

A fresh model-only positive-chain run then made seven logical/seven HTTP starts:
generation selected the corrected bicycle topic over the older scooter profile;
the source reviewer repeated its contradictory verdict, and the one allowed
reconsideration returned supported. Selection, Chinese expression, fidelity and
final source review completed; a synthetic delegated intent was registered and
reopened identically with zero provider calls. No dispatch or preference record
was added. Credential export was removed and production start time unchanged.

This demonstrates actual protocol recovery and preparation, **not clean semantic
acceptance**. The model explicitly rationalized away the source's synthetic/
unverified qualification during reconsideration; final wording again omitted it.
Same-family reviewers do not settle that engineering concern. Preserve the
raw contradictory response and this failure rather than describing seven calls
as a wholly correct cycle. Actual totals are now 152 logical / 165 observed HTTP
starts, zero actual sends. The run is retained under the owned scratch
`model-only-feedback-cycle-20261015-r3/results/report.json`.

Next evaluate qualification-preserving interpretation on varied evidence, not a
single synthetic keyword patch, and continue longitudinal temporal
deferral, attributed learning, full host integration, migration and production
acceptance. A clean protocol does not prove a useful or truthful decision.
