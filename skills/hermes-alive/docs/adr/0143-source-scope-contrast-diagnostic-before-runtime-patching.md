# ADR 0143 — Test source scope before adding another runtime rule

Date: 2026-10-15. Status: bounded diagnostic evidence; runtime unchanged.

## Question and decision

ADR 0141/0142 preserved a concrete failure: model wording dropped a fixture's
synthetic qualification, and a same-family review rationalized that omission.
That is not sufficient evidence that all source limitations are generally lost,
or that hardcoded disclaimers, a keyword filter or another schema would solve it.
The fixture-envelope status and a material limitation asserted inside a source
must also be distinguished. Do not retrospectively turn the old failure green.

Add a reproducible opt-in diagnostic, not a production behavior patch. It tests
attribution/availability uncertainty, preliminary small-sample research,
conditional live/recording access, and an ordinary clear public notice. It retains
raw input/output, model route, stage failures and counts. It never invokes a
channel adapter, registers an intent, updates preference or grants authority.

`probe_alive_live_source_scope.py --output <empty-private-directory>` runs actual
interpretation and the current retained-candidate review, plus explicitly
diagnostic negative contrasts. Contrast results are **not** fabricated canonical
review receipts. The contrast path still runs if interpretation abstains.
`--contrasts-only --contrast-mode scope` checks subtler omissions without repeating
generation already inspected. The ordinary-notice scope contrast is a positive
control, not an instruction to reject every shortened message.

Model budgets are 16 logical calls and 48 observed async HTTP starts per run;
the canonical review may use its existing single protocol recovery. Output must
be empty, errors stay errors, and `semantic_quality_qualified` remains false.
The injected-model unit fixture verifies accounting and preservation, not semantic
accuracy. Source-scope fixture claims are synthetic and not external references.

## Actual evidence

Two terminal, model-only isolated runs used the configured model route, without
production writes or actual sends:

1. `model-only-source-scope-20261015-r1/results/report.json`: 11 logical / 11 HTTP
   starts. Three actual proposals preserved material source scope: an attributed
   unverified listing; a preliminary non-peer-reviewed pilot of 12 participants
   with its outcome limits; and an ordinary free public tutorial. Their reviews
   accepted them. The conditional-access case abstained for insufficient practical
   detail; this is an observed relevance judgment, not proof of optimal usefulness.
   All four directly contradictory contrast messages were rejected.
2. `model-only-source-scope-20261015-r2/results/report.json`: four logical / four
   HTTP starts, contrast-only. Reviews rejected unqualified availability from an
   unconfirmed repost, generalized improvement from the pilot, and free access
   with omitted eligibility/recording restrictions. The ordinary faithful short
   notice was supported. No keyword-specific patch or universal disclaimer was
   added to obtain those results.

These give useful counterevidence to a generalized scope-loss diagnosis, but are
small same-family diagnostics. They are not independent adjudication, complete
expression/authorization/delivery chains, held-out longitudinal usefulness, ten
clean production cycles or proof that omissions cannot recur. No model/fallback
settings changed. Cumulative actual counts: 167 logical / 180 observed HTTP
starts, zero actual sends. Both credential exports were removed after terminal
state, and production startup time remained unchanged during the jobs.

Report files are private (`0600`) and created by the container user. Ordinary
host copy was denied; evidence was inspected using bounded network-disabled
read-only helper containers. Do not widen Profile or artifact permissions merely
to inspect it, or rerun inference because copying failed. Helpers use `--rm`.

## Qualification and next action

The probe's direct and scope-only accounting tests pass on Windows and offline,
read-only, resource-limited Linux overlays. They prove four/12 fake-call behavior,
raw evidence retention, no overwrite and no actions, not production installation.
The scripts are registered in portable CI; full portable CI was not run here.

Keep the original source-scope concern open, and require material qualifications
to survive fresh end-to-end expression tests. Do not spend indefinitely polishing
a synthetic label while leaving the autonomous loop unfinished. Next connect
bounded reconsideration to persistent agenda/host cadence: repeated unchanged
silence should not buy new model work each tick; temporary deferral must not become
permanent dislike or infinite silence, and new evidence/feedback/consent changes
must invalidate stale decisions. Continue attributed reflection/learning, full
host/channel integration, privacy/physical forgetting, portable lifecycle,
migration/rollback and actual production acceptance under the original objective.
