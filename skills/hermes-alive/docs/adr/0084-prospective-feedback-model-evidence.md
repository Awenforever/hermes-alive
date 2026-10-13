# ADR 0084 — Real feedback interpretation exposes unit-isolation failure

Status: bounded real-model evidence and generic unit quarantine implemented.
Not automatic learning qualification, ten-case success or production acceptance.

## Prospective setup and recorded calls

Ten public synthetic cases and provisional author constraints were written before
the calls. No private conversation, model/default/fallback change, actual channel
send or email. The probe builds synthetic fixture authorizations/receipts and
retained input, then calls the actual FeedbackSynthesizer. This exercises the
interpretation component, not a real delivery or a complete Alive host chain.
The earlier learning fixture can now receive its exact synthetic sent text; its
default behavior remains unchanged. Its pre-existing fixture preference signal
is not exposed to the interpretation prompt, and no new signal is written.

First batch: three logical calls and three observed async HTTP 200 responses;
reported model `deepseek-flash`, provider `custom:ustc`. Mixed topic/meeting feedback,
polite acknowledgement and factual correction all complete structurally. The model
separates lasting topic interest from situational timing, leaves acknowledgement
without preference signals, and marks correction-related interpretation uncertain
or situational rather than treating the corrected weekday as verified truth.

One additional configured-model review reports `qwen3.5` / `custom:ustc`, one
logical call/one HTTP 200. All three interpretations are judged acceptable with
limitations. This did not confirm the initial concern about correction-related
candidate dimensions as a material error, so no example-specific correction was
applied. Reported model families differ, but share the service frontend; backend
identity, world truth, reviewer correctness and independence are not established
merely by model labels or mutual agreement.

Second batch: three new cases, three logical calls/three HTTP 200. Ambiguous stop
and quoted injection-like example complete structurally; irony fails validation.
The older probe preserved only error_class, not the rejected model output. That
missing evidence was a diagnostic defect, not proof the model missed irony.

A separate explicit diagnostic experiment repeats irony once after adding raw
synthetic-output capture. One logical call/one HTTP 200; source prompt and semantic
algorithm unchanged. The model understands sarcasm and supplies three valid
reply-grounded hypotheses, but a fourth uncertain-topic hypothesis quotes the
assistant's original message instead of the user's reply. The old whole-output
validator rejects all four, losing the three usable hypotheses. The original
failed records and reports remain unchanged; the repeat is not a new case or a
successful semantic run.

## Fundamental change: independently accountable interpretation units

Signal validation now isolates individual invalid units. It neither fixes their
text nor guesses their source. Valid hypotheses survive unchanged; rejected
signals carry their original indexes and fixed reason. The encrypted bundle keeps
the original model findings once, and recovery re-runs the same unit validation.
Processing contract v2 records accepted/rejected counts; receipts expose those
counts and all_signals_structurally_valid. V1's previously valid raw findings remain
readable, without rewriting original journal events or failed experiments.

The public probe marks partial interpretations structurally_completed=false,
while retaining interpretation_completed, findings, rejection count, raw synthetic
response and actual model/provider. Parser completion with quarantined units is
not zero-error coverage. Automatic learning authority and semantic accuracy proof
remain false, including when every unit passes. No profile/weight/job/message
is created. Malformed top-level protocol or unavailable consent/evidence still
fails the operation; per-unit isolation does not loosen source or permission rules.

This is not an irony keyword patch, fuzzy quotation repair, permissive role swap
or alternate-model hardcode. It fixes the general defect where one unsupported
subunit erased unrelated evidence-grounded interpretation. Reprocessing the retained
actual diagnostic output without a new model call retains three signals and
quarantines index 3. That is a processing result, not a claim the raw model was
correct or that the original failed operation now succeeded.

## Evidence anchors

- First input tree `6f8114604afb7c2dcb99c6d65d9f40230bb61ce9`, archive SHA256
  `8af15ba16992f4e43ef296d4725a5e42186bacba66cd70a61b1574116d3f43ed`.
  Container alive-feedback-live-20261013-r1 exited 0, start
  `2026-10-13T15:46:41.434129025Z`, finish `2026-10-13T15:47:19.892039608Z`.
  Report SHA256 `5150b2e32a7001529c84cf309d1a450ce834ea841c0f47e90238803b6687ee6b`.
- Review container alive-feedback-review-live-20261014-r1 exited 0, start
  `2026-10-13T16:48:36.870737574Z`, finish `2026-10-13T16:49:06.518265081Z`.
  Report SHA256 `681842c90c8c2c3f4bd3627cc98eb09bb18aae01bc5902143482a8b8010fc86d`.
- Second batch alive-feedback-live-20261014-r2 exited 0, start
  `2026-10-13T16:53:30.683600863Z`, finish `2026-10-13T16:54:02.274109661Z`.
  Report SHA256 `314ac03f63a0838a178777cf4133b062a3c667d62066306d6ce6f5564dddfc4d`.
- Diagnostic input tree `5ec3329790084cfc76bba3db80a7ad572841f40d`, archive SHA256
  `bd177269276c6c5adac5266818ef7722c620b12bcad083e0505dc54b3d26584b`.
  Container alive-feedback-live-20261014-r3 exited 0, start
  `2026-10-13T16:57:37.283889706Z`, finish `2026-10-13T16:57:55.012230943Z`.
  Report SHA256 `a10810d650bdfbd5b2c224f9eef145f432763f1d706d8c34a63d96314a9c4957`.

All exact temporary model exports/configs were removed only after verified
terminal containers and checked absent as root. Production remained running,
original start `2026-10-11T07:43:25.630569081Z`. No other-plugin/wmw/configuration
change. Cumulative actual logical model calls: 51; observed async HTTP attempts: 63.
Failed interpretations and diagnostic repeats are counted, not hidden.

## Verification and remaining objective

Local tests cover valid/invalid mixed units, malformed individual units, assistant
quote masquerading as user evidence, partial receipts/recovery, unchanged preference
signals, raw rejected output preservation and exclusion of provider exception
secrets. Existing learning-context, preference, reflection, outcome and evaluation
regressions pass. These do not qualify semantic coverage or real host identity.

Immutable staged tree `de2ea72d8b61fd7f71470eb32f28b10383095e9f`, archive
SHA256 `f3665e3842883b5faeaf3f8ac49486c64ea04b7adba022eff6e412a0a1f160ef`,
also passes feedback_synthesis, feedback_probe, learning_context,
preference_learning, reflection, outcomes and evaluation on the isolated managed
Linux Python 3.13 environment. Container alive-feedback-units-offline-20261014-r1
has network disabled and a read-only scratch mount; exited 0, start
`2026-10-13T17:16:49.179001081Z`, finish `2026-10-13T17:16:56.329841053Z`.
The probe suite's two reported logical calls are fake model responses, not additional
real-model calls. This is component regression evidence, not installation,
latest-core portability or complete host-chain qualification.

Six distinct cases have been attempted; only five originally completed structurally,
and only the first three have cross-family review. Four corpus cases remain untested.
No continuous ten zero-error complete Alive calls, real feedback learning, attributed
user benefit or production acceptance is established.

Continue new-case model/independent-review qualification and prospective utility,
including how incomplete hypotheses are handled without human babysitting or
silently claiming preference authority. Keep natural expression, authenticated
onboarding/feedback/delivery, layered/external memory, agenda/adaptation, migration,
derived-copy forgetting, rollback and portable lifecycle/production acceptance
in the full objective.

## Subsequent four prospective cases: protocol reliability remains unqualified

On the immutable unit-isolation tree above, presentation preference and relative
postponement complete without quarantined signals. Explicit topic boundaries are
understood in the raw output, including separate celebrity opposition and
city-policy/technology support, but all three units omit `uncertainties`. All three
are quarantined; the summary and unresolved meanings survive. This is not a
semantic misunderstanding, a successful complete interpretation or permission to
fabricate missing limitations. The fourth case, a follow-up question, completes
with uncertain topic scope and no durable preference claim.

The previously shared rejection reason incorrectly described missing protocol
fields as absent original evidence. Diagnostics now distinguish bounded protocol
violations from quotes absent from the owner's reply, with a regression for a
missing uncertainties field. This does not relax the output contract or repair
the model's response. No new live call tests this diagnostic-only revision yet.

- Batch r4: three logical calls / three HTTP 200, model deepseek-flash,
  provider custom:ustc; two structurally complete, one partial with three rejected
  units. Container alive-feedback-live-20261014-r4 exited 0, start
  `2026-10-13T17:19:00.098379056Z`, finish `2026-10-13T17:19:25.378443152Z`.
  Report SHA256 `043fd5fb5d867f8984408e362db58c4eb736229ff9c77453d281b4693393168a`.
- Batch r5: one logical call / one HTTP 200, same reported route;
  container alive-feedback-live-20261014-r5 exited 0, start
  `2026-10-13T17:20:16.764160336Z`, finish `2026-10-13T17:20:24.637443935Z`.
  Report SHA256 `59324da1f3786c63398df6a9026c8f44150335ae9ad0610c8daaa694d9f743b9`.

All ten distinct prospective cases have now been attempted: eight first attempts
structurally complete, one initial operation failed and one partial interpretation.
The irony diagnostic repeat is not an eleventh distinct case or successful retry.
Only the first three have independent-family review. Cumulative actual calls now
55 logical / 67 observed async HTTP attempts. All six model-container batches are
terminal; all 24 exact exported credential/config paths are verified absent as root.
Production remains running with its original start time unchanged. No channel send,
new preference, private chat read, model configuration or production/wmw change.

Next qualification must address bounded model-driven contract recovery and
independent assessment of partial outputs, without deterministic invention of
missing semantic content, hiding rejected calls, permission escalation or erasing
usable units. Exhausting the corpus is not ten zero-error complete Alive calls.
