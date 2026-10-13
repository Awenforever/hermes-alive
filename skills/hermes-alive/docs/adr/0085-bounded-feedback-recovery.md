# ADR 0085 — Bounded model-driven recovery without invented semantics

Status: opt-in research component; synthetic regressions and one structural live
recovery demonstrated, with the preceding failure retained.
No production integration, automatic-learning permission or semantic proof.

## Evidence and decision

ADR 0084's real main-model response understood explicit topic boundaries but
omitted uncertainty fields in three units. An earlier response understood irony
but cited the sender instead of the owner in one unit. Dropping all usable evidence
is wrong; filling in invented defaults or laundering a retry into a clean first
run is also wrong. Generic recovery must preserve evidence and failure history.

FeedbackRecovery takes an existing valid partial FeedbackSynthesizer completion,
not arbitrary pasted model output. It revalidates the original consent, causal
delivery, complete input, encrypted content and original action binding. Only
quarantined indexes are offered to an injected Hermes model caller. The original
accepted units, summary and unresolved meanings remain immutable and visible.

The model can replace a rejected unit with a fully reply-grounded hypothesis or
explicitly abstain with a reason. Unsupported quotes or malformed replacements
remain rejected. Missing fields are not supplied by code. Index omissions,
duplicates, boolean indexes or attempts to rewrite accepted units fail the repair
contract. Recovery hypotheses are presented separately, not flattened into a
supposedly clean initial interpretation. A successful structural recovery is
still not semantic correctness or permission to learn.

## Budget, provenance and failure behavior

At most one canonical recovery attempt per parent completion, journaled before
the model call. Caller-chosen retry IDs cannot evade the bound. Timeouts,
cancellation, provider failures, malformed responses and withdrawal during the
model wait remain spent; no silent retry loop or new provider credential.
Routing/fallback remain Hermes' responsibility. Each result records actual route,
source/context/prompt digests and counts. Raw repair output is encrypted once and
cannot outlive the original retained feedback. Provider exception text is not
written to the durable journal. Recovery rechecks evidence after model wait and
again during use; erased/revoked/expired original evidence blocks it.

This module is not enabled in a runtime hook or command. Its model caller does
not get profile, schedule, channel-send or other action authority. Current research
still does not qualify real gateway owner authentication, semantic independence,
bounded tentative preference usefulness or physical cascading erasure of all
derived encrypted copies. Initial operations with malformed top-level responses
are not recoverable here: their raw output lacks a valid retained partial receipt.
Those remain failures, not covered by this component.

## Verification plan

Synthetic tests cover recovery, preservation of accepted parent units, explicit
abstention, unsupported quotes, omitted fields, index-target attacks, replay and
concurrent attempts, original input erasure, mid-call withdrawal/erasure,
cancellation and provider-secret exclusion. Test calls are fake, not real-model
evidence. Run the exact staged source on isolated Linux with network disabled,
then one real-model recovery against a copy of the retained public synthetic
topic-boundary experiment. Do not rewrite its original journal or call recovery
a new successful representative case. Keep independent assessment and the full
memory/agenda/adaptation/host/lifecycle/production acceptance scope open.

## Actual experiments and contract simplification

The first live-container setup failed before any model callback: the probe compared
derived rejection wording to a historical report whose wording preceded ADR 0084's
diagnostic correction. It now binds the report's original raw model document to
the canonical encrypted receipt digest, not incidental diagnostic prose. A fake
probe regression uses intentionally old diagnostic wording to prove this distinction.
The original test data are copied in an offline root test container because their
protected encryption-key permissions block the host SSH user; source permissions
remain unchanged. No production data are mounted.

The first actual recovery call (r2) returns three complete, reply-grounded signals
including uncertainties. However, the original repair protocol redundantly required
an outer reason on every replacement; the model omitted it on all three non-null
signals, and validation rejected the recovery. This design error repeated the
mandatory-field failure rather than adding semantic value. Non-null replacements
now require only index and signal: hypothesis and uncertainties already supply
their reasoning. An optional supplied reason is validated and retained, never
invented. Null/abstaining units still require an explicit explanation. Core source,
target, bounded signal and semantic evidence fields are not relaxed.

A fresh isolated copy of the original partial fixture (r3), not a replay of the
spent recovery operation, is an explicit repeat experiment after contract revision.
One actual main-model call recovers three signals, none remaining structurally
rejected. This is not an additional distinct representative case or a newly clean
initial interpretation. Both model outputs report deepseek-flash/custom:ustc;
each observes one async HTTP 200 from api.llm.ustc.edu.cn. Neither writes new
preferences or sends a channel message. Only structural correctness is established;
scope/permission-versus-enthusiasm semantics still need independent assessment.

- First source tree `41c49683b4be109a9ec620c4d14b4c0f121ffe95`, archive SHA256
  `67eef10bb891bd691952195d52cfacd6fb885259834f1a52f6e79800ef914961`.
  Eight isolated offline suites pass; container alive-feedback-recovery-offline-20261014-r1
  exited 0, start `2026-10-13T17:31:19.47668833Z`, finish `2026-10-13T17:31:32.699032731Z`.
- Setup container alive-feedback-recovery-live-20261014-r1 exited 1, start
  `2026-10-13T17:32:33.242254829Z`, finish `2026-10-13T17:32:34.586666109Z`,
  before the model callback or observed HTTP instrumentation; zero model calls.
- r2 source tree `6c17bcdc78f200784ac9c8739660f77d741ff808`, archive SHA256
  `f15b89cd1e56b88c0a1cc70770f306fdedfc6cc9a2db245aeba543f6b4d460fc`.
  Extended offline probe regression passes, start `2026-10-13T17:34:36.78394845Z`,
  finish `2026-10-13T17:34:41.450516491Z`, container exit 0.
  Live container start `2026-10-13T17:34:41.929721971Z`, finish
  `2026-10-13T17:34:51.211137404Z`; exit 0 reports the interpretation failure,
  not success. Report SHA256 `e7cb004184eda0a99415433f8057d9f6e25f3e0c36076091132d8d4e7dfa7ed8`.
- Final r3 source tree `f23400810e76751fd05cd07302a077d335c11804`, archive SHA256
  `77ec114d119591edaa1253f84658d138491239464f652f4140b7b63aba7bd49a`.
  Eight isolated offline suites pass, start `2026-10-13T17:36:58.400667052Z`, finish
  `2026-10-13T17:37:10.782119474Z`, container exit 0.
  Live start `2026-10-13T17:37:11.266295886Z`, finish `2026-10-13T17:37:19.715404074Z`,
  exit 0, three recovered units. Report SHA256
  `490e0d28fdaa8887c43942875ecacca56ebfad2ca0dcf913385a5a447e38cce1`.

Recovery-container credential/config exports (all 12 exact paths) are removed and
verified absent as root after terminal states. Production remains running, original
start `2026-10-11T07:43:25.630569081Z`, no production/wmw/other-plugin changes.
Cumulative actual model calls now 57 logical / 69 observed async HTTP attempts.
The offline probe's reported calls are fake and excluded from these totals.

Final code review strengthens the one-shot claim: it checks the canonical started
row inside the journal writer lock, rather than relying on an optimistic read or
timestamp-dependent conflicting append. A stale-read regression hides the started
record from the fast path; the atomic claim still refuses a second model call.
This claim-only strengthening does not revise the live model evidence above or
claim another live call. Its final local regression passes, as do all eight suites
on isolated Linux, network disabled/read-only scratch mount. Final tested tree
`8fd963787b1ff8bc46b1408807e16d2a64ab2088`, archive SHA256
`b39c94608ce98a6b5799e4b3cc7583cb5881835295608c887dd1215e1a601e49`;
container alive-feedback-recovery-offline-20261014-r4 exited 0, start
`2026-10-13T17:43:03.923329668Z`, finish `2026-10-13T17:43:15.534873747Z`.
An offline read-only-source audit confirms the original partial fixture still
contains one original synthesis completion and zero recovery events. Audit copies
SQLite files to container-local storage to allow WAL handling without changing
the original files; it does not infer pristine state from an unopened database.
