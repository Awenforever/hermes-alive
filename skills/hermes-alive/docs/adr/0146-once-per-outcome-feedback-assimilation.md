# ADR 0146 — Feedback interpretation becomes retractable cognition context

Date: 2026-10-16. Status: opt-in isolated integration; not production activation
or confirmed preference learning.

## Problem and decision

Literal paired feedback already reaches cognition (ADR 0140), but semantic feedback
interpretation remained an opt-in standalone diagnostic. Reinterpreting the same
reply on each tick wastes work; treating a model's interpretation as approved
profile facts or requiring the user to approve every hypothesis are both wrong.

Add `FeedbackAssimilationRuntime` to interpret a canonical attributed feedback
outcome once, then expose its current retained hypotheses alongside the raw pair.
It does not change `safe_for_automatic_learning=False`, admit preference weights,
approve a reflection, write typed memory, infer consent or authorize action.
It is a tentative semantic layer, not complete reflection/learning or proof that
its interpretation is correct.

The autonomous cycle explicitly opts in through `interpret_feedback=True` and
an optional Hermes-configured model selection. Routing, credentials and fallback
remain Hermes responsibilities. Reconciliation, current owner policy, pause and
transport attention still precede this work. Production defaults remain inactive.

## Processing and recovery

- Scan the owner's outcome journal forward with a separate owner/clearance cursor;
  default scan 16 records and at most one new interpretation attempt per tick.
  Further backlog is left for later ticks, not skipped to the newest few messages.
- Only reply/correction/dismissal/explicit-feedback kinds qualify. Metadata scope,
  consent, complete original input, exact delivered wording and canonical causal
  attribution are checked by the existing feedback snapshot before model access.
  A source is processed at its own sensitivity, never below host clearance.
- Operation identity binds owner and outcome, not the host cycle or current model.
  A retained completion reopens; failed/interrupted work is unresolved, not silently
  repeated using a new key. Cursor restoration/rescan does not mint retry permission.
- Fix an existing feedback interpreter race: the atomic start insertion must be
  newly created before calling the provider. A stale losing precheck no longer
  spends a duplicate model call. Cancellation still escapes, leaving spent work.
- Counts distinguish attempted, completed, retained, unavailable and unresolved.
  New provider failure does not erase other evidence. A failure before any durable
  start is not swallowed and acknowledged as processed. Cursor is progress only,
  never authority or a complete inventory certificate.

## Advisory context, privacy and bounds

Only this runtime's deterministic interpretation lane is read; earlier unrelated
research probe artifacts are not silently activated. Every read reloads current
snapshot/consent/retention/content integrity and actual model attribution. Owner
and clearance scope precede private content resolution.

Each advisory contains whole accepted mixed findings, quoted reply evidence,
scope and unresolved meanings, linked interpretation/outcome/input IDs and model
identity. It is labelled tentative, incomplete and not independently confirmed.
Seeing the raw reply and its interpretation is not two independent observations.
No support/opposition weight or permanent user fact is created. Structurally
rejected units remain excluded; their rejection metadata is not semantic approval.

At most three whole outcome packages, within 6000 JSON characters, are exposed.
Oversized packages are omitted whole rather than cutting away caveats. If present,
these hypotheses precede older weighted advisory within an 8000-character combined
budget; without them the existing reader behavior is retained. Raw paired feedback
is still available independently so cognition can challenge an interpretation.
Original retention bounds still apply. Withdrawal or erasure removes availability
and changes cognition/wait signatures, including during inference. General physical
cascade forgetting and multi-vault restore remain separate unfinished requirements.

## Evidence

Windows and network-disabled/read-only/resource-limited Linux pass the composed
fixture: once-only interpretation and cursor/restart; mixed whole hypotheses in
actual planning input; unchanged waiting without more inference; derived erasure
during a model await; foreign-owner isolation; private/restricted/public clearance;
raw input erasure; consent disabled before processing and withdrawn afterward;
provider failure without implicit reattempt; atomic insertion loser with independent
call counter zero; and no new profile/preference/reflection approval/action writes.
Linux adjacent weighted learning, raw paired feedback, bounded/model-reasoned
reconsideration and final expression preparation/correction pass. The original
feedback interpretation fixture also passes Windows.

These are module overlays over retained dependencies, not fresh installed-device,
full portable CI, cross-process lifetime or production qualification. The higher-
clearance read test exposed an overly strict equality filter; it now permits lower
sensitivity evidence while validating it at its original sensitivity. Private-case
real-model behavior below is unchanged by that scoping correction.

## Actual configured-model observation, not a utility claim

`probe_alive_live_assimilation.py` retains a bounded synthetic-only diagnostic with
raw prompts/results and zero actual channel calls. Terminal run
`model-only-assimilation-20261016-r1/results/report.json` made four logical / four
observed HTTP starts, two interpretation-plus-cognition cases:

1. Courtesy acknowledgement: the model retained an **uncertain** hypothesis, not
   topic enthusiasm. The next decision abstained; restart/unchanged context waited
   without provider callback attempts. Its rationale called the earlier guide
   “unrelated”, which is stronger than this small fixture establishes; keep that
   concern rather than calling the case semantically perfect.
2. Mixed feedback: interest, concrete methods/applicability conditions, objection
   to vague summaries and a meeting-related temporary deferral were separated.
   The next decision deferred. Some topic/presentation units were labelled durable
   while retaining unresolved scope; they are still tentative model hypotheses,
   **not** confirmed lifelong preferences or a measured learning success.

Both actual generation prompts were inspected: each contained one tentative
interpretation and one original raw pair. Both reopened with zero callback
attempts and added zero memory, preference-weight, action-attempt or dispatch
records beyond the pre-existing synthetic fixture. No ablation, independent family
review, positive-expression adaptation or longitudinal added value was established.

Cumulative actual totals: **177 logical / 190 observed HTTP starts**, actual sends
zero. The model task terminated, temporary credentials were removed and production
start time was unchanged during the job. No production/Core/Enhance/model/network
change, Gateway restart, release or deployment occurred.

## Continue the original objective

Qualify partial/failed interpretation recovery and broader longitudinal usefulness,
connect commitments and sustained agenda evolution, establish installed host
ownership/configuration identity and real feedback ingress, and complete layered/
external memory, privacy/forgetting, portable migration/rollback and real production
acceptance. This interpretation layer must not be presented as completion of the
full autonomous memory/learning kernel or ten clean production cycles.
