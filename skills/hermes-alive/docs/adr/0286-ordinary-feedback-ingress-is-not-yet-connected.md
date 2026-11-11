# ADR-0286 — Connect ordinary feedback, not just seeded interpretation

Audience: maintainers and QA. Purpose: record an observed integration gap and
the implementation/acceptance boundary for closing it.

Date: 2026-11-05. Status: gap reproduced; product integration pending.

## Evidence

The configured Kernel path in `admitted_inbound_bridge.py` calls
`record_configured_input`, which validates the current route and records a
metadata-only wake. It neither retains replies nor associates them with Alive
actions. The older shadow capture uses another identity contract and also
does not produce ordinary user feedback outcomes; it is not a drop-in fix.

`FeedbackContextReader` and `FeedbackAssimilationRuntime` consume validated
user response outcomes. Earlier composed feedback tests seed synthetic
historical response outcomes. Their interpretation/recovery/erasure proofs
remain bounded component evidence, not evidence of everyday learning.

`run_core_feedback_ingress.py` installs the plugin, uses actual Core 0.22.5
setup/confirmation and route binding, then dispatches three synthetic owner
inputs through actual `run_post_admission_hook`. Synthetic retention and
consolidation consents are present; no response outcomes are preseeded. All
three inputs remain unconsumed and are observed, but no feedback body, user
outcome or readable feedback context results. This diagnoses missing integration.

The supplier hook snapshot omits quote metadata even when the incoming event
has it. Arbitrary extra reply fields, temporal adjacency or a model-selected
recent action must not become proof of an actual quoted reply. This probe
starts at the post-admission dispatcher; preceding real-account authorization
and physical delivery are not independently qualified.

## Decision and implementation direction

Prioritize ordinary feedback integration before more share-style prompt
iterations. Reuse the journal, erasable vault, Core-scoped continuity and
feedback interpretation/erasure machinery. No new profile database, general
transcript reader, transport queue or model router.

- **Observation:** capture needs guided inbound-retention consent. Outbound
  retention, interest profiles and external-memory read permission do not imply it.
- **Association:** a verified quote and a main-agent semantic association have
  distinct provenance. Preserve the latter as a delegated interpretation;
  do not manufacture explicit reply/correction/approval evidence. Missing or
  ambiguous targets remain unassociated; the next message is not proof.
- **Learning:** interpret only with separate consent. Keep original scope,
  qualifications and contradictions. A sample-specific length opinion is not
  a permanent interest or an always-short rule. It grants no operation authority.

Core already presents scoped retained shares to the normal main turn. Prefer
that turn for semantic association, using a task-bound share reference and exact
current-input evidence, over a separate model invocation on every message.
This is an integration proposal, not an implemented or qualified interface.
Normal conversation and Enhance's independent token/FIFO ownership remain intact.

Guide new users through optional capture/interpretation. Existing installs remain
unopted-in; upgrades must not expand old consent. Unsent QA drafts plus this
conversation's reviews must not be imported as physically delivered feedback.

## Completion evidence required

Use an installed public-source plugin and actual Core normal turn, a real local
adapter submission, then fresh admitted feedback. Do not preseed response
outcomes or relabel submission certainty as a human having seen the message.
Cover immediate/delayed feedback, multiple possible targets, topical followup
without evaluation, quotations, situational refusal, correction and contradiction.

Verify opt-out, foreign scope, reset, missing/expired source, replay, revocation
during interpretation, cold recovery and erasure of originals/dependent advice.
A subsequent full Native cycle must receive correctly scoped evidence. Actual
models must demonstrate useful adaptation while preserving truthfulness, depth,
unrelated exploration and normal conversation. No automatic permanent-interest
update or operation grant follows from this path.

The known-gap probe must eventually become a full intake journey; retaining its
zero-outcome expectation is not the product goal. No sharing-quality credit.

## Diagnostic run record

r815 completed: three observations, zero retained feedback bodies, zero user
outcomes/context items, zero model calls and sends. r812 failed on the probe's
embedded-module lookup; r813/r814 counted the activation observation among the
test inputs. Failed traces are retained. r815 uses a pre-input event-ID baseline.
These fixture repairs do not repair the product gap.

## 2026-11-11 implementation and controlled qualification

Guided setup now offers `--confirm-share-feedback` in a private owner
conversation. The main turn can associate its current admitted input with an
exact retained share through a turn-bound reference. The journal records a
semantic association, linked to the original input and to an adapter success
report. The record preserves the exact input in the content vault for up to
the remaining share retention period. It grants neither profile writes nor
external actions. `/alive feedback off` clears current turn evidence and
withdraws the stored pairs from planning. Re-enabling permits fresh admissions.

The subsequent decision reads the original feedback and its provenance. A
versioned interpretation marker carries it into the drafting context even when
archive recall was unnecessary. Earlier recorded interpretations retain their
original feedback context contract.

The installed Core journey starts with an actual local adapter submission,
then runs an admitted synthetic user turn and a controlled main tool call.
It checks exact wording, replay, foreign scope, disabling, reopening the store,
erasure, and revocation during publication. The next-cycle case observes the
ordinary cadence wait and uses a simulated eligibility clock to inspect the
later decision. It exercises context flow with controlled model responses.
Real-model association and writing quality, cold Gateway recovery, and fleet
and production acceptance remain open.

The exact development candidate `5ebc94eb9d5d9425dd39b8efde2d6a5f0a318f6e`
passed the installed Core journey in r833. The later decision and source-led
author received the exact feedback and its provenance. The controlled final
review held the later draft and the controlled correction abstained. The
journey made one local adapter submission and earned zero sharing rounds.
An earlier run returned exit zero after the fixture raised an assertion in
the correction call. The final fixture checks the correction result and
fails on any fixture exception.

The real public-source attempt r835 ended with zero candidates and reached
none of the feedback turns. In r836 the installed Core produced a controlled
synthetic local share, then the configured official DeepSeek model handled
three admitted main turns. A quotation and a follow-up question produced zero
associations. An evaluation of the previous share produced one association
with the full input and an explicit one-off length scope. The model's ordinary
follow-up nevertheless inferred a measurement scale and comparability from
a source that said only that the trial reused an existing instrument. Its
acknowledgment also shifted from one share to similar topics. These examples
keep conversational accuracy and adaptation open.

The subsequent admission guard binds the turn to the platform message ID
from Core's structured current input. It retains the journal identity format.
The installed Core test r837 passed after adding a replay case with identical
text and different message IDs.

Exact candidate `fe455b096da221dc0a6b71efcdf7663f45a706fe` passed the
installed Core journey in r838. The real main turns in r839 used Core's
persisted platform message ID and reproduced the association counts of
zero, zero, and one. The follow-up again inferred unreported measurement
details. The acknowledgment again extended a single-share evaluation to
similar future shares. Both conversational issues remain qualification gaps.

In r841 the reply followed the recorded share-specific scope and kept future
length flexible. It still inferred a measurement scale, skipped validation,
and comparable results after reading the retained excerpt. A caveat about
the source followed those assertions. This run qualifies the observed
acknowledgment improvement and leaves factual follow-up open.

The configured owner can now list recent records, inspect exact original
wording and model interpretation by ID, and erase one feedback item. The
commands use the signed owner association and existing vault erasure path.
Controlled Core r842 verified inspection while processing is paused, refusal
across owner scope, managed backup removal, repeat erasure, and replay after
erasure. Hermes retains its own chat history under its history settings.

## 2026-11-11 route comparison and review erasure

The inherited main route in r845 used the configured custom provider for all
three turns. The reply kept the instrument unspecified, explained the limits
of the retained source, and kept the feedback acknowledgment local to the
share. The answer exceeded the requested one sentence. The official fallback
still inferred a scale and comparability in r841. The two route results and
the single synthetic subject leave broader conversational quality open.

In controlled Core r846, the owner erased feedback while the later draft's
final review was outstanding. A supported review response arrived after the
erasure. The candidate became unavailable before authorization, but a generic
source-support error failed the wake. The reviewer now distinguishes loss of
an initially validated evidence snapshot from provider and protocol failures.
The same scenario in r847 closed the wake as `evidence_changed`, with only the
initial share's authorization and local submission.

Controlled Core r848 exposed a separate retention gap. After the feedback
record and its managed backup were erased, one completed review snapshot
still held the exact feedback input. Its current-evidence check prevents reuse
for authorization. The encrypted copy remains until its own retention ends.
Item-level erasure therefore covers the original association today, with
dependent content originally pending.

New opportunity interpretations and source-review records, including retained
invalid model responses, declare their signed native feedback inputs at write
time. The vault records these references with the ciphertext under its writer
lock, bounds child retention to the earliest parent, and refuses publication
if an input was erased or expired. Item and expiry erasure traverse those
references and use the existing resumable managed-backup purge. Receipt
metadata and tombstones remain available for audit.

For pre-lineage records, the authenticated owner forget command traces
interpretation and review receipts. Final expression reviews link to the
model candidate rather than directly to its interpretation. The migration
checks the selected candidate's retained frame to recover the exact synthesis
receipt, without matching raw feedback against review prose. Controlled
installed Core r854 simulated the old writer and r855 exercised new writes
with legacy discovery disabled. Each removed the affected final-review copy
and its managed backup while preserving a different review for the same owner.
Local vault coverage separately verifies transitive deletion, owner scope,
restored dependency metadata, and rejection of a write after erasure.

The author now binds saved model candidates to the native feedback actually
included in their prompt. Correction documents and invalid semantic review
responses depend on that candidate. The legacy forget path traces the same
typed selection and expression chain for these records. Controlled installed
Core r858 and r859 each removed the affected authored text and source-review
snapshot while preserving a separate draft and review for the same owner.
The semantic review receipt retains structured dispositions and risk labels
for audit. Its eligibility check requires the candidate to remain available.

An executable contract now depends on its exact authored expression, so a
withdrawal removes the compiled body before an already prepared launch can
reuse it. A consented share context or delivery-history copy uses a
withdrawal-only dependency. It retains its own authorized lifetime and
survives routine expiration of the draft or executable contract. An explicit
withdrawal still traverses expired ancestors and purges ciphertext and managed
backups. The signed structural start and outcome receipts remain available.
Legacy feedback forgetting traces authenticated authorization, share and
delivery locators to remove records written before these links existed.
Previously supported cross-vault retention reconciliation remains in place.

Model selection rationale now depends on the native feedback inputs of all
admitted candidates in the selection prompt, including candidates that were
considered and passed over. The older-format lookup uses the recorded
exploration gate and the candidate-to-synthesis links from the authenticated
frame. Controlled Core r868 and r869 each removed the rationale for both
a selected draft and a subsequent model choice of silence on the same
candidate pool. A separate rationale and its draft and review remained
readable for the same owner.

Explicit feedback forgetting now includes the affected encrypted planning
frame with its model-written dimension reasons, and the separate candidate
bodies from the affected interpretation. It checks the original frame digest,
same-owner synthesis receipt, and candidate identity before accepting a
locator. Before erasing the frame, it records signed candidate-to-synthesis
locators, including the other candidates in that frame. These carry IDs and
the frame digest only. Later withdrawals can use the locators after the
encrypted frame is gone. The first and repeat owner requests were exercised
through controlled Core, with an unrelated frame and candidate preserved.

New planning writes bind candidate ciphertext to the verified feedback of
its own interpretation. The full frame depends on the union because it
contains model-written scores and reasons for the entire pool. The vault
records the links with the body, before any frame event can be published.
A new frame event contains the signed structural locators at publication,
so automatic expiry can remove its ciphertext without losing provenance.
Reused legacy candidate content is adopted only after exact identity,
owner, purpose, sensitivity and body checks. Existing frame receipts keep
their original retention references.

The deliberation store fault test interrupted publication after ciphertext
write, then applied expiry. It removed the orphan, linked frame, affected
candidate and managed backup, retained the structural event and independent
candidate, and removed that second candidate only after its own withdrawal.
Controlled installed Core r877 verified the old writer path. r878 disabled
legacy discovery for explicit erasure, then recovered the signed lineage
after the frame body was gone.

The SQLite storage version now advances from 2 to 3 without changing the
encrypted payload format or managed backup format. A prior runtime rejects
the upgraded store on open. It cannot claim readiness against state whose
retention rules it cannot enforce. Stop the outgoing Alive runtime before
the replacement opens the vault. A process that already opened the prior
schema is outside the startup guard.

The cross-version test seeds real version-2 state and a managed backup
using the previous code. The current runtime opens both formats, persists
a linked derivative and interrupts erasure before backup cleanup. The
old runtime refuses the migrated store. The current runtime resumes the
durable cleanup on cold open, then a newly created managed backup restores
the tombstones and unrelated history.

Core r884 used separate processes for previous runtime, upgrade, rejected
old activation, dormant rollback, and restoration. The old enabled plugin's
startup failed at the storage version boundary. Core's hook dispatcher
contained that failure. With Alive deselected, Core opened the same session
through the same fixture adapter and registered no Alive command. The restored
version retained the session, signed owner configuration, vault key and
unrelated history. It completed the pending purge without restoring either
body or creating a dispatch. The fixture uses local source trees and the
profile configuration API for selection. Package-manager admission and
platform service restart are separate fleet checks.

Independent exports, original Hermes history and complete volume snapshots
outside the managed backup root remain outside the vault erasure boundary.

## Evidence-grounded ordinary replies

Real r886 used the configured main route with a new synthetic public
fixture. The prepared share said a two-station pilot was planned and the
source said testing was scheduled and no passengers had used it. The main
turn answered the requested question in one sentence, correctly withheld
an accessibility-effect claim, and recorded the later one-share feedback
without promoting it to a lasting preference. Quote, follow-up and
evaluation association counts were 0, 0 and 1.

Real r887 used the configured official fallback as the isolated main
route and repeated the earlier instrument-reuse counterexample. A shorter
continuity instruction moved the answer into one sentence, but the answer
still called the instrument a scale and asserted established validity and
direct comparability. It made one model request for the follow-up with no
reference-tool turn. The earlier r841 response also overreached after
reading source evidence. A format improvement and a read receipt therefore
cannot serve as the claim-grounding gate. The r887 prompt overlay was
discarded. Both trials used controlled shares and earn zero fresh
sharing rounds.

Further qualification needs an explicit boundary for scoped, evidence-dependent
ordinary answers. Test both documented results and missing results. Preserve
short format, natural implications and unrelated turns. Any independent claim
review must operate before the relevant wording is exposed, or the streaming
boundary must be treated as an unresolved limitation. Run the two configured
routes separately and retain the exact answer, scope and evidence they used.
