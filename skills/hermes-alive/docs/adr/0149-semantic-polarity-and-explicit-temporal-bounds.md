# ADR 0149 — Semantic polarity is not an exact phrase; deadlines are not start times

Date: 2026-10-16. Status: isolated integration; expression usefulness still fails.

## Decisions

### Separate meaning preservation from exact-value preservation

The actual v1 planner sometimes emits a negation without protected literal
strings. Structural rejection says nothing about its semantic correctness; locking a
negative phrase verbatim also obstructs natural paraphrase. Conversely, inventing
an omitted literal or deleting negation would change the contract silently.

New communication plans request version 2. Negation and uncertainty atoms in v2
use explicit `literal_policy=semantic`: their complete meaning still needs semantic
review, but no particular phrase is mandatory unless an exact literal is supplied.
Deadline, amount, link and contact kinds remain exact-value kinds and cannot opt
into semantic-only protection. This is a general representation distinction, not
a special case for a reminder or a phrase substitution.

`SemanticAtom` defaults to legacy behavior. V1 documents serialize exactly as
before, without a new default field; v1 plans retain their original requirements.
V2 meaning serialization is emitted only when a semantic-policy atom exists, and
roundtrips preserve the explicit policy. V1 rejects the extra policy field; v2
rejects unsupported, explicit-default and noncanonical policy forms. Do not rewrite
old confirmed meaning, weaken old literal locks or infer user consent from v2.

Free wording remains REVIEW_REQUIRED, never deterministically proven merely
because literal lists are empty. Complete atom/polarity/uncertainty review still
applies; a sign inversion is rejected when identified by review. Supplied exact
literals still reject missing text even under semantic policy. Same-family review
can miss errors; neither old exact literal checks nor v2 establish factual truth
or authorize a message. Existing final wording, source and send-time grant checks
remain separate. No new delivery or learning permission is created.

### Make temporal constraints explicit in cognition

The actual purpose reviewer called a reminder before due_at “early”, even though
the original request said within twenty minutes. Supplying current time did not
fix an ambiguous representation of the target time.

Commitment cognitive evidence now includes explicit temporal_bounds:

- `not_before`: earliest availability, from canonical current available_at;
- `target_deadline`: target latest time, from original due_at;
- `active_until`: original agenda expiry, not proof of delivery or completion.

No new time is guessed, no original agenda field is rewritten and no task is
rescheduled. The existing availability filter excludes future not_before items;
a future target deadline alone does not exclude an otherwise available commitment.
Prompts explain the generic readiness/deadline distinction. The model still decides
whether an earlier reminder is useful, rather than a rule forcing share or silence.
Original wording remains authoritative if the intended timing is ambiguous.
Authenticated task intake must eventually bind “at/after” requests to availability
instead of treating all future timestamps as generic due dates. That ingress is
not yet installed or qualified.

## Verification design

New fixtures cover v1 byte-shape/roundtrip, v2 polarity/uncertainty roundtrip,
invalid policy injection/downgrade, attempts to relax exact-value kinds, unchanged
old missing-literal rejection, v2 no-literal negation, explicit literal enforcement,
paraphrase remaining review-required and negative review rejecting polarity shift.
These synthetic review verdicts exercise the contract, not model intelligence.

The composed test now includes a v2 commitment whose explicitly supplied status
is “not checked yet”, keeping a useful factual negation separate from operating
constraints. It traverses interpretation, source/purpose assessments, selection,
meaning, expression, delegated synthetic preparation and delivered-history erasure.
V1/legacy and one-purpose-correction fixtures remain. Separate time fixtures prove
an available due-by commitment is visible while a future-ready one is not.

Linux now imports the **whole current hooks/tests package** rather than stacking
module replacements over the old package. Retained Core/model dependencies are
unchanged; this is not a new Hermes installation or portable lifecycle acceptance.
Read-only, network-disabled, resource-bounded runs each execute thirteen scripts
through terminal completion, covering new policy and adjacent rendering/review,
selection, authorization, history, interpretation, feedback/reconsideration and
preparation/repair. Windows policy/legacy rendering/time fixtures pass, as does
the earlier composed v2 fixture; a final fresh composed Windows run is checked
separately before commit. Temporary failed-run cleanup restrictions from ADR0147
remain; no alternate cleanup mechanism is used.

Retained current-package snapshot r2:
`/tmp/hermes-alive-installed-RJbQNAiD/current-recipient-v2-20261016-r2`.
Its hooks/tests archive SHA-256 is
`db12f7f37ea7f1f6f4388ccc835f2ece8e9d3f87f8a2da2167870c4696620a5a`.
No production profile, keys or runtime data are part of that archive.

## Actual configured-model results: mixed, not acceptance

Private synthetic evidence under `/tmp/hermes-alive-installed-RJbQNAiD/`:

1. `model-only-meaning-v2-20261016-r1/results/report.json`: four actual calls.
   V2 negation is structurally usable without invented literal fields. Source
   review supports the reminder; purpose review rejects timing and the single
   correction abstains with a future reconsideration. The “within means wait until”
   critique was itself questionable and motivated explicit temporal bounds. This
   does not prove correct timing or a good natural message.
2. `model-only-meaning-v2-20261016-r2/results/report.json`: six actual calls using
   the complete current package with explicit temporal bounds. Selection now
   chooses the reminder; meaning/expression/fidelity complete, with a fixed UTC
   deadline and no obsolete relative countdown in final text. However, generation
   still places operational prohibitions inside recipient meaning, and the purpose
   reviewer accepts them as assurance. The final message still recites constraints.
   This is a failing naturalness/purpose example, not a clean acceptance cycle.
3. `model-only-purpose-current-20261016-r1/results/report.json`: four actual purpose
   reviews of fixed synthetic proposals, not model-generated full chains. Both
   reminder contrasts match expectations. Eligibility now explicitly asks to be
   told participation conditions: visible conditions pass and hidden conditions
   fail. All four expectations match. The source request changed to remove an
   ambiguity, so this cannot retroactively turn ADR0148's earlier mismatch into a
   pass or establish improved performance on that old case.

Each job terminates, removes its temporary model export and checks production
StartedAt unchanged during that job. Offline/evidence containers auto-remove;
no actual channel or email sends. Totals **218 logical calls / 231 observed async
HTTP starts**, failures included. No independent-family qualification, production
change, deployment, main merge or release follows from these results.

## Next decision, not another phrase patch

The isolated purpose contrasts succeed while full-context assessment still calls
redundant operating limits useful assurance. The planner's self-declared recipient
goal and safety-heavy context may anchor the evaluator; this is an hypothesis,
not an established cause. Compare compact purpose-first interpretation against
the present draft-first pipeline on fresh, blinded, paired synthetic/public
scenarios, including explicit requests for assurance and important factual limits.
Retain raw failures and do not label same-family self-approval as independence.
Do not add a rule banning all negations, delete a particular disclaimer, or force
action to improve a success rate. Robust semantic production, useful sustained
agenda and the full memory/feedback/host/privacy/migration/rollback/portable and
production goals remain unfinished. New mode stays opt-in and undeployed.
