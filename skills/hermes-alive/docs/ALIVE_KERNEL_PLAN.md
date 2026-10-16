# Hermes Alive Kernel — Living Development Plan

Status: active

Last reviewed: 2026-10-16

### Delivery milestones and ownership (user clarification, 2026-10-14)

The delivery estimate is approximately 35%, an engineering estimate rather than
an acceptance score. Foundations and isolated contracts are substantially built;
the complete autonomous decision/expression/delivery/feedback loop is not yet
integrated or qualified. Production remains on the legacy runtime. Report progress
against these milestones, not test counts or individual interface probes:

1. Integrate a useful, bounded autonomous loop in isolation with exact provenance,
   model choice, retained memory, agenda and outcomes connected end to end.
2. Demonstrate longitudinal usefulness and safe silence on new synthetic/public
   scenarios, including restart, consent withdrawal and failure recovery.
3. Qualify installation/upgrade, migration and rollback, then obtain production
   deployment authority and complete real production acceptance.

Weixin FIFO, queued-message management and context-token refresh belong to
hermes-wechat-enhance, not Alive. Alive must use the host/channel transport
contract and must not create a competing platform queue. Its durable action
outbox tracks intent/evidence/recovery; it is not permission to reorder or resend
the platform FIFO. Host ingress probes establish observation fidelity only.
Failure with a replaced high-level worker does not prove a queue defect.

The earlier permission to repair confirmed wechat-enhance defects during Alive
work is superseded by the 2026-10-15 Qoder handoff for concurrent ownership.
Codex now records and coordinates such findings rather than editing Enhance;
Qoder independently owns its repair work. Shared interface changes require
explicit coordination. No speculative core/queue or production edits follow.

2026-10-16 ownership update: the user explicitly reassigned Enhance integration/
distribution closure to Codex and Email Watchdog to Qoder. That supersedes the
previous scheduling/ownership for this scoped handoff, not module boundaries.
Enhance work stays in a separate repository; it still solely owns FIFO/token.
Alive's experimental kernel is not deployed by that work. Shared production
windows remain explicit and independent: an approved Enhance restart does not
authorize an Alive/Core/email deployment or a second restart after rollback.

### Current integration milestone: delivery evidence and attributed feedback

2026-10-16 — ADR-0162 exposes and fixes a genuine missed native-feedback interface
defect: FeedbackSynthesizer's per-call timeout was not accepted by native callers.
Bounded narrowing now reaches the real child/request budget; protocol/host tests
pass. A new prospective real-model series completes four native calls: feedback
interpretation, concise suggestion, explicit topic-pause abstention, and return
after explicit withdrawal of that pause memory. User/scenario are synthetic;
no channel sends, production edits or private chat reads. Secret projection was
removed after the terminal container and no pending children remain.
This is NOT zero-error: the last candidate omits a material fictional-source
qualification while its risk rationale incorrectly says it was preserved.
Structural rejected_count0 is not fidelity. Next exercise versioned recipient
meaning plus source/purpose review and correction through final wording, not a
specific phrase patch or more route probes. Actual endpoint/physical HTTP total
was not instrumented; four new logical calls all report deepseek-flash. Full
host installation, longitudinal memory/agenda/outcomes/learning and production
acceptance remain open. Preserve this failed semantic example as evidence.

2026-10-16 — ADR-0161 composes the acquired native caller with the actual durable
host lifetime and authenticated owner policy. A cycle-bound parameter factory
gets the journal's exact operation ID after opening/recovering it; factory errors
cannot replace that identity or fabricate completion. Native cycle authority
closes on exit and uncertain children block new work until terminal cleanup.
Actual Core r3 passes initial synthetic silence, unchanged-context reconsideration
without inference, real owner pause during an in-flight child (failed receipt,
no successful close), then paused recovery without a new model call. Windows
host lifetime and caller tests pass. The r2 test incorrectly expected the raw
worker error rather than synthesis's normalized failure; preserve that failed
test and its corrected receipt-level evidence. No production changes or real
model/channel calls. Explicit profile/config/grant/family inputs and automatic
installation/scheduler wiring remain unfinished; move next toward qualified
real-host grants and sustained native behavioral scenarios, not more interface
checks in place of memory/agenda/outcome/learning usefulness.
Final r4 also fixes a discovered grant-currentness gap: withdrawing the host's
credential-name grant invalidates an existing capability before another secret
read, even without a configuration edit or whole-Alive pause. All four actual
Core integration markers pass. Revoke/regrant ABA still requires a host-owned
monotonic authorization generation; do not claim polling detects unseen history.

2026-10-16 — ADR-0160 now connects actual current Core home/secret scopes to
the owner-bound caller and native child, without ambient secret discovery.
Default/alias/primary403->backup pass on actual retained Core in a network-none,
read-only owned container. A real controlled in-flight child completion is
rejected after host lifecycle revocation; terminal workspace closes. The canonical
Alive shadow cycle uses the same acquired caller and replay does not call again.
Parent environment remains unchanged. This is controlled synthetic evidence,
not real model/semantic quality, ten clean rounds or production acceptance.
The host lifecycle/config/grant readers remain explicit synthetic inputs in the
probe; automatic production-host factory and auth/transport coverage are still
open. Next connect the authorized factory and advance sustained useful native
behavior, memory/agenda/outcome/reflection integration. No production restart or
change was performed; no model-call count increment.

2026-10-16 — Resumed Alive after the separately authorized Enhance3.4.2 urgent
release/deployment window closed. The preceding turn was concrete progress for
that inserted task, not completion of the Alive objective. Alive remains isolated
and undeployed; neither that restart authority nor its CI qualifies this kernel.

The owner-bound native caller now acquires a fresh model capability per request,
checks subject/profile/operation and revision validity around scoped credential
reads, detaches model-only data, and excludes ambient credentials/profile/code
paths from the child environment. Unit tests cover revoked/mismatched bindings,
malformed projections before secret reads, detached snapshots, budget exhaustion,
concurrent acquisition rejection and retained uncertain-child retry blocking.
These tests replace the worker; they prove the parent boundary only, not actual
Core capture, process cancellation or intelligent autonomous usefulness.
Adjacent snapshot/protocol suites pass on Windows. Actual host acquisition and
native child integration remain next; then resume longitudinal decision, agenda,
memory/outcome/learning qualification rather than expanding boundary probes
indefinitely. No real model calls, channel sends or production changes this turn.

2026-10-16 — ADR-0159 connects explicit model-only host snapshots through the
owned native worker to actual Core default/alias/fallback/secret resolution and
the canonical Alive shadow cycle. Conflicting ambient keys do not override the
owner; missing credentials do not become an implicit no-auth grant. Actual
controlled OpenRouter wire preserves per-model pins and data-collection deny,
without leaking unrelated custom endpoint headers. Core-created private pools
stay in that process, not serialized. Replay makes no extra native call.
Full r9 probe passes; failed r1/r3-r8 assumptions are documented, not counted as
successful rounds. No real model/channel calls or production edits. Automatic
owner-bound capture/minimal environment, other transport/TLS/auth lifecycles,
sustained semantic usefulness, learning/Halo/portability and production remain
open. Next build real host capture and proceed to longitudinal native behavior;
do not let routing probes substitute for the original intelligent-kernel goal.

2026-10-16 — ADR-0158 adds an opt-in, model-only private client policy boundary.
Actual Core primary403 -> named fallback preserves endpoint-specific/common
headers and credentials; canonical shadow/replay still passes. The anonymous
custom fallback lost its endpoint headers in r1/r2 and remains unqualified;
preflight now refuses that policy combination rather than silently losing it.
Provider routing/capability args are forwarded, not yet full on-wire privacy
qualification. No production/model calls/sends. Complete host snapshot/resolver,
per-model routing, other transports/TLS/credential lifecycles and sustained
native intelligence remain open, not replaced by this intermediate boundary.

2026-10-16 — ADR-0157 qualifies actual Core home/secret/alias/fallback semantics
with two synthetic owners (A→B→A), scoped key_env and ambient-key exclusion.
Original config/env bytes and context restoration hold; Core's readonly loader
still creates LKG backups and first-use scaffolding, so no filesystem-zero-write
claim follows. Complete official Git548e66f source, retained dependencies,
controlled metadata HTTP, denied DNS/connect/subprocess; no model calls/sends.
Prefer host-owned bound snapshot plus private-process resolution; full routing/
privacy/header/TLS/pool projection and automatic native caller remain to build.
This is sequential evidence, not concurrency, fresh-install or quality proof.

2026-10-16 — ADR-0156 connects an opt-in ModelCaller to a dedicated native worker:
canonical parent/context/route/identity request binding, private minimal Profile,
strict completed output and current-binding recheck, retained uncertain work with
terminal-only cleanup. Host-supplied Hermes route callback owns model/alias/fallback;
no invented default, profile copying or automatic gateway enablement. Actual Core
controlled tests pass primary/alias and403->declared-backup with correct keys, then
canonical Alive shadow/replay without another worker call. Real fallback exposed
v1 logical-id/attempt conflation; v2 evidence uses explicit exact started_at markers
(not time windows/order), preserving old contracts as old. Windows real protocol-
child tests and pure event tests pass; not actual Windows Core, live provider health,
model quality or installed profile auto-resolution. No new real calls/sends.
Next qualify actual host-scoped capability/presentation projection, then real
sustained native shadow intelligence. All memory/agenda/learning/Halo/forgetting/
migration/portable lifecycle/production gates remain, not replaced by RPC tests.

2026-10-16 — ADR-0155 adds a single-use managed model-process lease with bounded
input/output, retained asynchronous startup, timeout/cancel stop, terminate/kill
and actual child wait. Pending startup is uncertain, not terminal or permission
to retry/clean; original capture handles remain until that same worker ends.
Native Windows real-child tests pass. The actual Linux Core shadow runs inside
this supervisor; a second Core process held in its first synthetic API request is
cancelled and waited without accepting partial output. Python descendant denial
blocks Core/SDK ancillary probes; test challenges the guard instead of pretending
no attempts occurred. No arbitrary process-tree, parent-death or cross-restart
worker adoption proof, encrypted temporary bytes, real model/cancel-provider or
fresh-install qualification. Next build the admitted worker protocol with exact
parent/context binding, current Hermes model/fallback and consented identity;
then real sustained shadow behavior. The full original objective stays active.

2026-10-16 — ADR-0154 implements bounded, explicitly registered NativeCompletionHub:
random owner-bound session/task scopes, native pre/post/error correlation and exact
final text/model evidence, not last-model guessing. Real PluginManager lifecycle
dispatch supplies evidence in the actual native shadow chain; replay/withdrawal/
forgetting still pass. Early SDK-role assumption failed against Core's normalized
response and was corrected from the actual contract, not a Core patch. Pure-event
Windows/Linux tests cover concurrency, denied finalizations, duplicate/late events,
cancel/dispose and bounds. No raw prompt/body, new memory authority, sends or real
model calls. Cancelling evidence is explicitly NOT stopping a worker/HTTP request.
Next use a managed isolated process with bounded cancellation, authoritative wait,
current model/profile inheritance and durable outer operation replay. A cancelled
to_thread await is insufficient; do not activate the diagnostic synchronous caller.
Keep the full host/learning/privacy/portable/migration/production objective active.

2026-10-16 — ADR-0153 uses the actual retained Hermes AIAgent/prompt/SDK/turn facade
with physical HTTP controlled, rather than a high-level fake worker. Native SOUL
and ephemeral task reach the provider request, tools/external memory/project files
are excluded. Canonical Alive typed memory/commitment/discovery/attributed feedback
reach shadow planning; reopening spends no new call, withdrawal/forgetting exclude
old context from the next fresh session. Three fake replies, zero actual model or
channel calls, no network attempts in the final expanded run. Early incorrect
cache/policy/helper assertions and native model-field assumptions are preserved.
The host's served_model is not necessarily the completion-body model; do not ship
a guessed attribution adapter. This is not native Windows/fresh install, independent
semantic quality, long-term learning, external Halo or complete erasure proof.
Next qualify a scoped/recoverable host-call and completion-evidence boundary, then
real-model shadow behavior; preserve all original production/lifecycle requirements.

2026-10-16 — ADR-0152 screens a single direct contribution on six fresh synthetic
scenes, using original sources/context and a fixed owner-time anchor. Six real
calls: four messages/two silences, all valid envelopes, but ordinary instruction
recital remains and one external observation loses its canonical link. Requested
first-person assurance and source-strength boundaries improve in these individual
samples; no comparative superiority, independent review or production quality
claim follows. Direct auxiliary composition is not the host-native agent/persona.
No runtime switch is adopted. Totals290 logical/304 observed HTTP starts, zero
actual sends. Next inspect and compose the actual host/memory/agenda/outcome shadow
loop, not another round of auxiliary prompt patches; all original privacy,
forgetting, learning, migration/rollback, portability and production gates remain.

2026-10-16 — ADR-0151 actually removes a prior draft/goal from purpose interpretation,
then compares both paths with the same renderer/language on six new synthetic
scenes. Seventeen configured-model calls yield more informational replies, but
ordinary scope recital remains; assurance loses actor scope, and source summaries
become stronger whole-source/verification claims. No extra purpose stage is adopted.
One isolated user-named qwen3.8-reasoner attempt observes a timeout/retry and stops
after one logical/two HTTP starts with no returned model; no403, quality or
independent-family conclusion is inferred. Production configuration stays unchanged.
Totals284 logical/298 observed HTTP starts, zero actual sends. Fake Windows/Linux
tests qualify mechanics only; raw evidence is archived privately outside temporary
storage. Next compare host-native/direct contribution composition and explicit
actor/modality/time relations, not more disclaimer rules or unreviewed deliveries.
Preserve the whole host/memory/agenda/adaptation/privacy/migration/portable and
production objective; current production remains on the legacy runtime.

2026-10-16 — ADR-0150 tests current/compact contracts crossed with requested output
order on six new synthetic scenes (24 calls per protocol). First-run fixture and
schema parity defects are preserved and corrected in a complete second run, not
selective retries. Corrected cells:13 structural candidates/10 abstentions/1 invalid
JSON; none of the four arms solves ordinary scope recital. Longer contracts also
infer personal ineligibility without evidence and skip preliminary leads; compact
ones can convey caveats but add source/control commentary. No winner, independent
review or production acceptance claim. Field order is not hidden reasoning order.
Add exact interpreter system-prompt method hash/requested-model audit metadata at
the call boundary, with explicit no-material provenance; no runtime prompt/model
switch. Totals266 logical/279 HTTP starts, zero actual sends. Next qualify a genuine
source/context-only purpose stage before any draft/claimed candidate goal, including
timing relation, unknown affiliation, assurance and meaningful silence. Keep the
complete memory/agenda/learning/host/privacy/migration/portable/production goal.

2026-10-16 — ADR-0149 separates exact-value protection from semantic polarity in
new v2 plans/meaning while preserving v1 byte shape and locks. Negation/uncertainty
may be paraphrased, never dropped; free generation still requires semantic review,
and exact dates/amounts/links/contacts cannot relax their policy. Explicit agenda
temporal_bounds distinguish not-before from target deadline without rescheduling
tasks or forcing a decision. Actual v2 generation avoids the prior literal failure;
full-context selection reaches expression with a fixed deadline, but redundant
operational recital still survives purpose review. Four fixed-proposal purpose
contrasts meet expectations after making eligibility necessity explicit; that is
not full-chain success or a retrospective pass for the old ambiguous fixture.
Current whole-package offline regression replaces module overlays for this phase;
fresh installation/lifecycle remains unproved. Totals218 logical/231 HTTP starts,
zero actual sends. Next test compact purpose-first versus draft-first interpretation
on fresh blinded scenarios, rather than patching phrases or trusting self-approval.
The complete sustained agenda, memory/adaptation, authenticated host/feedback,
privacy/migration/rollback, portability and production objective remains active.

2026-10-16 — ADR-0148 adds explicit recipient-meaning plans and a separate model
purpose assessment: immutable old contracts remain old; strict new mode separates
recipient content from proposed operating constraints and supports actual remind
speech acts. Grounded planning reviews facts and purpose separately, with at most
the existing one correction generation. A purpose receipt cannot substitute for
factual support or sending authority. All-malformed plans become unresolved, not
qualified silence or another implicit provider spend. Actual trials still expose
bad content classification, literal-contract failures and correlated reviewer
misses. A four-case fixed-proposal purpose diagnostic meets three expectations,
not a complete semantic claim; the fourth's necessity/context must be examined.
Fresh composed selection exposed missing current time, now explicitly anchored
and persisted with a retry-stable decision timestamp. No subsequent live success
is claimed for that context fix. Totals204 logical/217 HTTP starts, zero sends.
Continue robust plan production, recipient purpose/final wording and temporal
usefulness, then the unchanged full host/memory/learning/privacy/migration/
portable lifecycle/production objective. No production deployment or ten-clean
semantic-cycle acceptance; new mode is isolated and opt-in.

2026-10-16 — ADR-0147 connects admitted current commitments, without discovery,
to the composed cognition/selection/expression/preparation pipeline. No current
representable material now idles with auditable zero-provider work. Current task
changes invalidate interpretation; typed agenda vault binding and delivered-history
dependencies fix a real preparation/erasure integration gap. Two actual five-call
trials reach shadow selection but still fail naturalness/timing quality despite
support/fidelity approval. Totals 187 logical / 200 HTTP starts, zero actual sends.
Next address purpose-aware intent/meaning/expression rather than phrase patches;
also qualify handed-off intent invalidation with Qoder, bounded-view coverage,
custom vault binding and authenticated host ingress. No deployment or acceptance.
The private Linux regression runner's early successful SystemExit stopped the
suite after two tests; the corrected terminal run proves all eight completions:
commitment cognition, action authorization, delivered history, opportunity
synthesis, feedback assimilation, semantic reconsideration, final preparation
and repair. Fresh Windows commitment cognition and authorization also pass.
No claim of full CI, fresh install or ten clean semantic cycles follows.

2026-10-16 — ADR-0146 integrates once-per-outcome feedback interpretation with
the opt-in host cycle and retractable advisory context. Current consent/source/
clearance and raw paired feedback remain authoritative; no typed profile, weights
or action permission are written. An atomic start-race bug is fixed. Windows/
offline Linux mixed feedback, restart/no-spend, withdrawal/erasure, failure and
scope fixtures plus adjacent regressions pass. Four actual calls show uncertain
courtesy and separated mixed feedback reaching next cognition; no ablation or
longitudinal utility proof, and some scope/relevance judgments remain tentative.
Totals 177 logical / 190 HTTP starts, zero actual sends. No production deployment.
Continue sustained commitments/agenda and genuinely qualified reflection/learning,
installed host/feedback ingress, full privacy/migration/rollback and production
acceptance; do not equate this advisory layer with completed learning.

2026-10-15 — ADR-0145 connects source-linked model reconsideration hints to the
bounded wait ledger and original agenda IDs. Timing anchors to original prompt
time, never extends on reopen, cannot exceed host/source limits or authorize a
send; new information still wakes early. Windows/Linux fixtures and adjacent
regressions pass. One actual six-call story defers for an explicit 45-minute
meeting, waits across restart with no inference, then responds to early availability
with qualified wording. No permanent preference, action attempt or actual send.
Totals 173 logical / 186 HTTP starts; credentials absent, job terminal and production
start unchanged during it. This is not general commitments, reflection/learning,
longitudinal usefulness or production acceptance; those full-scope milestones remain.

2026-10-15 — ADR-0144 integrates opt-in bounded, change-sensitive reconsideration
with the existing autonomous cycle/host. Only verified silence can wait; each
later wait revalidates original planning with inference forbidden. New owner
input/effective context/erasure/policy/configuration or time boundary invalidates
it; reuse/restart does not extend the window. Transport reconciliation and pause
still precede waiting, with no competing FIFO. Windows and offline Linux composed
fixtures pass; this is not installed lifecycle or real-model temporal judgment.
Next connect model-reasoned deferral and persistent commitments/agenda to this
host boundary, then qualify meaningful autonomous feedback/reflection and the
full migration/privacy/channel/production loop. No production deployment, model
calls or actual sends in this work; totals remain 167 logical / 180 HTTP starts.

2026-10-15 — ADR-0143 tests source scope before patching runtime. Four varied
synthetic source contexts and direct/subtle contrasts make 15 actual logical /
15 observed HTTP starts: preserved attribution and study limits, three material
omissions rejected, ordinary concise positive accepted. Conditional access
generation abstained; usefulness not established. These same-family diagnostics
do not erase ADR-0142's failed fixture qualification or qualify the complete loop.
No new runtime restriction/disclaimer/filter added. Totals 167 logical / 180 HTTP
starts, zero sends; model jobs terminal, credentials removed, production unchanged.
Next prioritize durable, bounded reconsideration and event-sensitive cost control
alongside continued full-chain qualification, not endless per-fixture gates.

2026-10-15 — ADR-0142 adds one explicitly bounded malformed-review recovery in
planning. Original invalid output is encrypted, not normalized into approval;
reopen validates recovery lineage and never repeats a spent operation. Valid
unsupported/uncertain reviews and provider/independence failures do not loop.
Ten synthetic modes and Linux adjacent regressions pass. A fresh seven-call real
chain demonstrates bounded recovery, synthetic intent preparation and no-spend
reopen; it again loses source qualifications while same-family review approves.
Do not count that as clean semantics. Totals 152 logical / 165 observed HTTP starts,
zero actual sends; credentials absent and production start unchanged. Continue
qualification-preserving cognition, temporal deferral and genuine feedback
learning within the unchanged full host/privacy/lifecycle/production scope.

2026-10-15 — ADR-0141 real preparation is mixed, not qualified: a meeting-pause
proposal required critique/regeneration; courtesy did not become preference; an
explicit correction changed selection, but the first positive path hit a private
fixture route-vault mismatch. A corrected-route rerun then stopped on a contradictory
model review, not successful silence. Different-family review returned 403; no
independent semantic result. Cumulative actual totals 145 logical / 158 observed
HTTP starts, zero actual sends. Credentials absent and model jobs terminal.
Send preparation now checks owner/host route contract before inference, retaining
all post-model authorization/launch checks. Windows and isolated Linux fixture
passes; Linux adjacent context/preparation/repair matrix passes. No production,
Core, model or Qoder-owned Enhance changes. Next bounded review-protocol recovery,
positive full-chain qualification and meaningful temporal deferral/feedback/learning,
with the unchanged full production objective. Do not count these as clean cycles.

2026-10-15 — ADR-0140 connects literal delivery-linked feedback to the next
interpretation and source review, with source times on explicit memory rather
than forcing an unqualified paraphrase into permanent preference. Candidate
evidence retains feedback lineage; new opportunity content cannot outlive its
included feedback. Reopen/model-await checks reject withdrawal/erasure changes.
No preference/memory update or new model-feedback interpretation is performed.
This is feedback context, not completed reflection/learning. General physical
cascade forgetting, gateway-owner qualification and production migration remain
open. No new real model calls (132 logical / 145 observed HTTP starts total).
Latest Windows and isolated resource-limited/offline Linux pass the composed
fixture including oversized-input preservation. Linux also passes explicit-context,
registered-intent, expression-history and all final preparation/repair modes.
The first overlay regression used a stale facade exception alias; fixing that
private test wrapper restored its expected rejection handling, not a runtime fix.
The new fixture is registered in portable CI; full CI/fresh install is not proven.
Next actual-model feedback meaning and useful retractable learning/full-loop
qualification, without a competing FIFO or Qoder-owned Enhance changes.

2026-10-15 — ADR-0139 actual interpretation uses registered intent/outcome context
in four new synthetic histories: three unchanged contributions are not proposed
again, while a distinct new method remains eligible. No invented delivery/user
feedback in engineering inspection; no ablation, independent semantic review,
or longitudinal utility proof. Four real calls/four HTTP starts: cumulative
132 logical / 145 observed HTTP starts, zero real sends. Job terminal, model
export absent and production unchanged. The versioned opt-in diagnostic retains
failure/raw-output evidence and explicitly checks no new attempts/dispatch; it
does not automatically run or activate learning. Next useful unresolved-intent
settlement and grounded feedback/tentative learning, not more blanket gates.
The diagnostic fault-observability fixture passes on Windows and isolated
resource-limited/offline Linux, and is registered in portable CI. The full CI
pipeline and fresh-install lifecycle have not been rerun for this diagnostic.

2026-10-15 — ADR-0138 connects registered communication attempts and separately
validated canonical outcome facts to the next interpretation and source review.
It is not a queue/pending-state detector or another FIFO. Current context changes
invalidate retained decisions; erased content cannot remain usable. The first
composed fixture exposed an incorrect default outcome-vault connection, fixed
to match the explicitly selected send-runtime vault. Latest Windows passes the
fixture, including reopen and in-flight erasure. Resource-limited, network-disabled
Linux passes it plus expression-history, all four final-preparation and all five
final-repair modes. These use retained-module overlays, not a fresh installation.
The four regression entrypoints are now included in portable CI; the entire CI
pipeline has not been rerun this turn. Outcome recording time/order are explicit.
Next real longitudinal usefulness and unresolved-intent admission/delivery/feedback.

Actual bounded final-wording recovery now has limited model evidence: nine logical
calls/nine HTTP starts, all on the configured model, one unchanged positive control
and two seeded false claims corrected and re-reviewed; zero repeat calls on reopen.
No send. Initial planning/render/review were synthetic, not full semantic or utility
qualification. Cumulative counts: 128 logical / 141 observed HTTP starts. The first
launch failed before inference because of its isolated profile setup; credential
exports were removed after terminal state. Production was unchanged.

Enhance ownership has been handed to Qoder through the user-managed handoff.
Codex will not concurrently edit its repository/experimental branch/production
Hook, manage its queue or restart production. Alive continues in isolation;
shared interface changes need explicit coordination. The public Enhance baseline
and unpublished transport experiment remain separate, not an implicit dependency.

2026-10-15 recovery audit: all five latest Windows final-wording repair modes
now pass, including correction-ancestry validation. Recovery and alternate-critique
tests independently count forbidden provider invocations: raising an assertion
inside the callback was insufficient evidence because bounded repair deliberately
contains provider exceptions. The counter remains zero in all modes. This closes
a test-observation blind spot, not a new runtime defect or real-model semantic
qualification. No model calls, sends, deployment or production changes followed.

ADR-0137 remains in semantic/utility qualification: one source-guided final-wording correction slot per
selected intent, followed by fresh fidelity/source review; no automatic rewriting
of exact confirmed text, no sibling generations and no recursive repair. The
latest extension also binds correction ancestry into final support and core
dispatch revalidation. Latest Linux checks pass all five repair and four final
preparation modes. Latest Windows successful repair includes sibling and late
ancestry-erasure refusal; the existing preparation regression passes. Earlier
Windows full repair modes passed before the ancestry extension, not a full latest
Windows matrix or genuine semantic/utility proof.
No new real model call or production deployment. Continue useful longitudinal
behavior and the full pending/delivery/feedback/memory/agenda/portable objective;
do not count this bounded mechanism as ten clean production cycles.

ADR-0136 adds exact-final-wording source review in grounded mode and carries its
requirement in authenticated authorization through core outbox execution checks.
It distinguishes correlated review from independent corroboration; a rejected,
uncertain or unresolved review does not become permission or successful silence.
The previous actual full-chain probe used nine calls: one supported development
share and one correction silence, no repair, zero sends. Its semantic quality
remains explicitly unqualified. Cumulative real counts: 119 logical / 132 observed
async HTTP starts. The temporary credential export was removed after verifying
the model job terminal; no new real model call or production change this turn.
Next qualify bounded final-wording recovery and fresh longitudinal usefulness,
then pending/delivery/feedback/memory/agenda/portable production gates. Do not
mistake a durable quality constraint for independent truth or user benefit.

Qualification evidence: authorization, preparation, semantic review/store and
autonomous cycle regressions pass on Windows. The final-wording fixture covers
supported, unsupported, interrupted/reopened and valid local-launch paths, plus
witness substitution/removal and direct-outbox denial after erasure. Isolated
Linux passes that fixture with network disabled and a read-only retained-module
overlay; this is not fresh-install evidence. The first Linux invocation omitted
the temporary profile path; the next exposed a stale exception-class alias in
the overlay loader. Both harness faults were corrected, not counted as passes
or hidden as runtime successes. Test containers are auto-removed; no real send.

ADR-0135 integrates opt-in grounded candidate review and one evidence-bound repair
into planning and through the existing expression path. Windows/Linux synthetic
tests prove partial-failure isolation, retained good choices, repair/reopen and
honest correlated-vs-independent review. It is not installed/activated and models
remain host-configured. Next real full-chain critique/repair and final-wording
grounding (including single-family semantics), then longitudinal utility and the
remaining pending/delivery/feedback/memory/agenda/portable production gates.

ADR-0134 real history ablation shows useful unchanged/new/correction distinction
but repeated unsupported prior-communication/user-history claims. Prompt-only
clarification does not qualify them. Source-support review now sees typed prior
wording; USTC Qwen3.8 independently identifies one real error and accepts one
grounded development, with one timeout. Next wire grounded critique/correction
into autonomous decisions without hard-coded model dependency or whole-batch
abort. No ten-clean-cycle or production claim; real totals 110 logical / 123
observed async HTTP starts, zero sends, unchanged production configuration.

ADR-0133 adds bounded authenticated/erasable prior wording to opportunity
interpretation and binds its snapshot across await/recovery. Windows and isolated
Linux synthetic tests verify context inclusion, recovery and privacy boundaries;
existing Windows expression regression passes. Generated wording is explicitly
not delivery, preference or authority. Real-model novelty/usefulness is unproven;
next compare unchanged/new/corrected evidence across fresh operations, then
trustworthy pending/delivery/feedback context and unresolved-intent controls.

ADR-0132 carries canonical actual renderer origin through the publisher seam,
checking owner/selection/exact body after fresh launch validation. Immediate and
deferred host-defined chunks retain that model despite conflicting foreground
turn evidence. Synthetic physical IO is not actual model or delivery proof.
Production remains unchanged; continue real-model longitudinal usefulness,
novelty/unresolved-intent controls and attributed feedback before activation.

ADR-0131 adds explicit bounded host lifetime and authenticated owner/lane-scoped
cycle allocation/progress. Windows/Linux host-state tests prove reopen, completion,
budget, stop/external cancellation cleanup and configuration/mode/owner isolation.
Actual composed modules plus native-SDK/synthetic-IO test two host-driven silence
cycles without another action attempt. No gateway daemon is registered; qualify
process ownership, unresolved-intent/novelty/cost controls, blocking work, public
lifecycle and paired migration before activation. Real-model longitudinal utility
and the full feedback/memory/agenda/portable/production requirements remain open.

ADR-0130 composes reconciliation/current user policy with planning/expression,
authorization and once-only publisher submission in a host-invoked cycle. New exact
owner/attempt lease selection avoids taking unrelated eligible work; old cadence
regression passes. Windows and Linux actual-SDK synthetic IO prove fresh-operation
composition, reopen/no extra provider spend or send, shadow/no attempt, silence and
pause/withdrawal. Synthetic positive reviews are NOT real-model semantic or utility
qualification. Next lifecycle/cadence/operation ownership and fresh real-model
multi-cycle scenarios, then attributed feedback/longitudinal and portable production
gates; current publisher remains Weixin-specific and production is unchanged.

ADR-0129 composes bounded owner binding discovery, trusted publisher resolution,
current-policy revalidation, host withdrawal and durable observation consumption
in one explicit host tick. Windows and Linux actual-SDK synthetic IO prove bad-row
isolation, owner filtering, scan/reopen/wrap, timeout and pause during async
resolution without another send or outcome. Returned keyed stage diagnostics
retain no private errors. It is not a production timer or a full global-pause
transaction; qualify lifecycle/cadence/cursor ownership, shutdown, retirement and
writer/performance, then join useful autonomous planning/expression/feedback and
real-model longitudinal utility. Portable production gates remain unchanged.

ADR-0128 connects explicit canonical owner pause to an enhance-owned withdrawal
interface (development `6b9b41f`). Windows and Linux actual-SDK synthetic IO prove
scoped pending removal, unrelated FIFO preservation, persistent deny/new-submit
suppression, in-flight partial ACK honesty, forged/stale policy refusal and deny
reassertion after simulated restore loss. Alive never edits FIFO or promises recall.
Not yet an automatic pause command: qualify cross-thread control, failure/capacity,
deadlines, migration and bounded subscriber lifetime; then meaningful autonomous
scheduling/feedback/longitudinal utility and portable production acceptance.
No production activation or enhance final release follows from this development.

ADR-0127 qualifies four composed failure cases in Windows/fake and Linux/actual
SDK synthetic IO: original error, caller cancellation after queue acceptance,
publication-table failure after IO and user pause immediately before launch.
Original error/result/cancellation survive, consumed starts do not resend and
pause blocks invocation. Caller cancellation does NOT withdraw host FIFO entries.
Next add authorized host-owned outstanding-submission cancellation/reconciliation
for genuine user pause/revocation, without Alive editing FIFO or promising recall
of in-flight/acknowledged messages. Keep consumer/writer/finality/feedback and full
longitudinal, portable and production scope; no activation follows from these tests.

ADR-0126 adds bounded durable consumer checkpoints after authenticated observation
ingestion, atomic unchanged-head checking and writer-lock replay. Windows and
Linux actual-SDK synthetic IO verify interruption/reopen, late ACK, unhealthy
cursor freeze, concurrent-reader conflict/recovery and checkpoint tamper refusal,
without sends or outcomes. Enhance development commit `95138df` exposes ledger
epoch/snapshot high-water to refuse reconstruction/observable rollback. This is
not full restore detection or a background subscriber; qualify lifetime, adverse
send paths and performance, then autonomous scheduling/finality/feedback and
longitudinal usefulness. Reader/state migration and production acceptance remain
open; no production change or enhance release follows from these tests.

ADR-0125 binds the qualified enhance publisher to a canonical Alive attempt/start
and composes prepared execution with once-only queued submission and local report
ingestion. Windows/fake and Linux/actual-SDK synthetic IO prove replay/scope,
reopen/late ACK and exact multi-chunk association without outcomes/reauthorization.
The initial Linux single-bubble test assumption was disproved; the corrected
oracle checks every host-defined chunk, not changed transport behavior. These
are SQLite reports, not cryptographically authenticated remote delivery or feedback.
Next qualify consumer lifetime, writer/performance and adversarial send failures,
then finality/ambiguity, feedback and the full useful autonomous loop. No production
activation or enhance release; keep direct-observer refusal and portable acceptance.

ADR-0124 develops a host-owned durable queue-submission/physical-ack producer on
enhance's separate `feat/alive-transport-evidence` branch (`ff80ccb`), not release
or production. Windows and Linux actual-SDK/synthetic-IO prove scoped two-binding
FIFO/reopen/cross-task drain and metadata-failure/no-resend behavior; old queue
rows retain NULL correlation. The bounded ledger denies complete delivery/quote
proof. Next qualify publisher identity and Alive attempt-bound reconciliation,
finality/ambiguity and feedback; preserve the direct-observer refusal. No new
source clone/snapshot or residual test container, no production activation.

ADR-0123 tests the exact production enhance queue source with synthetic IO:
outer normal return can mean merely queued, while same-task deferred drain bypasses
the outer observer. This is not a FIFO defect. Direct observation now refuses that
known queued seam before consuming the execution start; Windows and Linux confirm
the gap/refusal and stock-SDK direct regression. Integrate a transport-owned durable
attempt-bound receipt publisher (immediate/deferred/expiry), not task inheritance
or a competing queue. Never activate the stock-only observation seam on production
enhance or infer delivery from queued acceptance. Final enhance cleanup remains
after Alive; autonomous-loop and longitudinal acceptance are still outstanding.

ADR-0122 connects prepared planning/expression/authorization to an explicitly
qualified stock-adapter call with closed trace publication in finally. Success,
error/cancel and publication failure pass Windows/fake IO and Linux/actual SDK
synthetic IO; no publication failure resends or replaces an original result.
The adapter owns FIFO/tokens/retries, and no canonical delivery is inferred.
Shared-worker ownership, writer shutdown/performance and production activation
remain unqualified; continue them and canonical history/feedback before acceptance.

ADR-0121 persists closed local chunk traces on an existing authenticated attempt/
start, with owner/route/nonce binding, anonymous counts/references, interruption/
scope flags and exact replay. Windows and isolated Linux publication/CLI regression
tests pass. These local traces cannot become canonical delivery results, complete
inventory or preference evidence. Next wire a qualified producer lifecycle and
queued ownership, then canonical delivered history and attributed feedback;
retain scheduling/onboarding/model/longitudinal/portable production requirements.

ADR-0120 reproduces/fixes late observer publication after unload during suspended
IO and makes repeated close safe. Post-await active checks, explicit pending-close
coverage and finally-owned counters preserve original return/error/cancellation.
Windows and Linux barriers/stock-adapter synthetic-IO regression pass. Queued
worker ownership and durable attempt-scoped publication are still unqualified;
continue them without rewriting FIFO, then integrate feedback and live runtime.

ADR-0119 adds a research-only owned chunk observer: identical delegation, no
FIFO/token/retry ownership, own-task/route capture, anonymous bounded references,
fail-open metadata and ownership-safe restoration. Windows contracts and actual
Linux stock send loop with synthetic IO pass, retaining seven normal returns or
one before partial failure/cancellation. No canonical delivery/history or live
queue qualification follows. Next qualify shared/queued ownership and durable
attempt-bound receipt publication, then feedback. Tests leave no containers.

ADR-0118 runs the actual stock Weixin constructor/send loop with only chunk IO
replaced. Seven successful chunk acknowledgements yield only the last client ID;
zero-effect failure and failure after a prior effect expose the same error fields;
cancellation can follow an accepted chunk. Never infer no effect/safe retry from
failure or promote final IDs into full delivery/quote proof. Next qualify an owned
send-boundary observer without touching FIFO/token/retry ownership. The probe
auto-removes its test container and reuses the retained snapshot after cleanup.

ADR-0117 measures the actual generic chunk helper returning only the last message
ID. CLI observations now retain only scoped anonymous report references, explicitly
not complete bubble inventory, delivery proof or canonical quote targets. Windows
parsing/scope tests and Linux host/cadence regressions pass. Do not promote these
reports into delivered history or inferred feedback. Next qualify actual outbound
receipt capture and owner/quote binding; production/queue behavior unchanged.

ADR-0116 composes discovery/planning/expression/delegation/preparation with the
actual Hermes send command in an isolated local-sink harness. Exact wording,
success/reject/partial/skip reports, foreign-lease rejection and single launch
pass; old host-expression regressions pass too. Actual command observation is
not external delivery, canonical target feedback or user benefit. Next integrate
delivery/history/feedback, authenticated controls and bounded scheduling, then
actual model/channel and portable production qualification. No production change.

ADR-0115 adds explicitly signed natural-expression delegation, default disabled.
Historical grants never expand. Current owner/policy/route/kind/sensitivity/expiry
and revocation checks apply at authorization, permit replay and start/launch;
existing cadence tests remain green. Windows and isolated Linux prove synthetic
preparation/revocation contracts, not external transport or model quality.
Next compose actual Hermes delivery and authenticated opt-in user onboarding,
then attributable feedback and longitudinal utility. No production change.

ADR-0114 composes current expression with existing send-time authorization and
one stable action attempt. Missing/exact confirmation, no implicit provider or
attempt duplication, and canonical policy withdrawal pass Windows/isolated Linux.
No transport was launched. The existing exact-expression confirmation restriction
is NOT a final autonomous product: next implement explicitly scoped/revocable
natural-expression delegation without expanding existing grants or treating
model reviews as permission, then compose host delivery and attributed feedback.

ADR-0113 composes current planning and natural expression/review. Silence has no
expression calls; completed recovery revalidates original evidence and consumes
no provider budget. An injected crash after the native comparison but before the
outer receipt recovers through authenticated retained records, not another call.
Windows and isolated Linux pass synthetic tests; no automatic delivery authority,
real semantic quality claim, watcher activation or production send follows.
Next compose send-time authorization and qualified host delivery, then feedback.

ADR-0112 adds a real PlanningRuntime composition from retained discovery through
model interpretation to current intent/silence. Reopened completed operations
reuse evidence and selections, incomplete provider stages do not silently retry,
and changed host policy/model/authority is refused. Windows and isolated Linux
pass controlled planning/cancel/recovery contracts. The watcher does not invoke
it yet; next compose expression and authorization without adding a channel FIFO,
then prove delivery/feedback and longitudinal model quality. Production unchanged.

ADR-0111 returns to the autonomous-loop milestone with four reopened planning
cycles: no advice/silence, synthetic feedback/share proposal, explicit boundary/
silence, withdrawal/silence. Actual projections and cognition preserve scope,
provenance and non-restored action authority on Windows and isolated Linux.
Controlled model fixtures prove plumbing, not semantic judgment or user benefit.
Next compose the runtime loop and qualify real-model longitudinal decisions;
do not mistake another structural test for an integrated production Alive.

ADR-0110 demonstrates actual adapter bundling can rewrite quote targets while
retaining the own-message bit; native complete text is normalized-event evidence,
not a single wire message. A delegated public busy-handler observer sees original
authorized inputs before merge and rejects actual shared-slot unauthorized input.
Individual FIFO fails with the high-level worker substitute (which removed drain
promotion), not proven bad SDK logic. Next qualify a real worker/provider seam and
consented busy-wire provenance before feedback; production behavior is unchanged.

ADR-0109 runs actual constructor/_handle_message/stop with the real Alive plugin
and a replaced HIGH-LEVEL agent worker. Native observation, deny/slash/busy gates
and error/cancel slot cleanup pass. First teardown raced background persistence;
actual stop fixes the harness. This is not provider/history/FIFO/delivery proof,
and the research quote handoff is still not consumed by Alive. Next qualify the
local adapter/worker/delivery path and explicit feedback, retaining the full goal.

ADR-0108 replaces the synthetic pre-pinned routing shortcut with actual receiver
ownership, route matching, served-profile checks and home resolution. Actual
scoped auth uses the transport's grant, not the runtime destination's allowlist;
an unserved route rejects without fallback. The first harness auth failure exposed
missing gateway multiplex-mode bootstrap and is preserved. Receiver/source data
remain synthetic, full session/transport/lifecycle proof is outstanding, and the
real Alive observer still does not consume experimental quote metadata.

ADR-0107 finds actual profile-manager separation breaks the instance-local
handoff. A task-private, runtime-home-bound research handoff restores scoped SDK
delivery without a global identity pool or core patch. Actual loop timers and
task teardown clear state; empty scheduling contexts avoid retaining profile
secrets, and consumed callbacks are removed. Synthetic pinned identity is not
live routing/auth/session proof. The actual Alive runtime is still not connected
to this experiment; canonical target mapping and real lifecycle are next.

ADR-0106 tests a bounded, in-memory metadata handoff through actual pre-dispatch
and post-admission SDK hooks. Synthetic auth/quote/bot and real rewrite directives
work or fail closed as intended without a core patch. The actual Alive runtime
does not register the experiment. Real multiplex/cache scoping, busy/replay,
physical cleanup and canonical delivered-target mapping still need qualification
before attributed feedback can use it. Do not confuse quote metadata with
delivery proof, human consent, learned benefit or the full Alive objective.

ADR-0105 exercises actual Hermes authorization/pairing admission before native
capture: default deny, approval, revoke and rejected routes are verified with
synthetic local state. It also demonstrates that authorized bots can reach the
observer while the SDK drops is_bot. Native principal kind stays explicitly
unknown, not human feedback. Next qualify a bounded metadata handoff or explicit
verified target-selection interface; slash hooks do not share native message
identity. Full gateway/session/profile/real-transport proof remains outstanding.

ADR-0104 adds opt-in native full-input observation with canonical retention
consent, encrypted erasable text, stable replay and writer-time revocation checks.
Actual SDK discovery exposes/fixes an embedded-import defect hidden by local
hook paths. Native input remains distinct from an agent turn or attributed
feedback; ordinary dialogue is never consumed. Quote/owner/profile qualification
and useful longitudinal feedback integration, not merely callback presence, are
the next milestones. Production and public releases remain unchanged.

ADR-0103 corrects an overly broad ingress assumption: the actual native
post_gateway_admission SDK supplies full event text and stable inbound IDs,
where agent hooks supply truncated previews. Real isolated registration/dispatch
passes; quote-target metadata is absent and the helper test is not actual gateway
authorization proof. Named-file provenance matches a clean pinned upstream tree;
_hmwa names alone are not evidence of custom patches. Next compose consented
native observation/target attribution, not more assumptions about message previews.

ADR-0102 extends cleanup ownership across watcher replacement and startup recovery
using their real shared OS lock. Busy is not completed maintenance or permission
to send; lock-file presence and cancellation are not live/terminal evidence.
Two-instance and separate-process tests cover controlled handoff. Actual installed
gateway reload/kill/reboot, external locks/storage and full portability remain
unqualified. No production restart/service/config change or real model call.

ADR-0101 connects privacy maintenance to the running watcher before send gates
and during interval waits, independently of proactive pause/cadence. Owned task
shielding prevents cancellation-driven duplicate workers; unknown completion or
erasure failure blocks further proactive work. Real synthetic storage deletion
through the watcher is tested, not just scheduler spies. Fully disabled-service
registration, teardown, long-tick timing, transitive erasure and performance still
need qualification. No new production task, service, consent or model call.

ADR-0100 adds metadata-only history erasure to existing local retention maintenance
and startup recovery, not just later reads. Signed ownership/storage checks guard
deletion, and unresolved dependencies remain visible. Tests cover absent readers,
separate context storage, backups and repeated startup. Periodic/privacy-command
integration, transitive copies, external storage and race/large-history behavior
still need qualification; startup alone is not universal timely forgetting.

ADR-0099 connects exact, canonically delivery-linked history under prior outbound
consent to feedback snapshots after executable expiry. Independent history cannot
grant resend or learning permission. Fixed action/context vault dependencies cover
custom profile storage and explicit forgetting; history verification erases an
invalid derivative, but immediate live cascade/maintenance is not yet connected.
Next qualify actual host capture/receipt production and proactive forgetting, then
useful attributed learning; do not treat synthetic receipts as provider proof.
No extra real model calls; cumulative totals remain 95 logical / 107 HTTP attempts.

ADR-0098 identifies a prerequisite for delivered-history retention: automatic
expiry and explicit forgetting previously shared item tombstones. Expiry now
records a distinct cause using unchanged physical erasure/backup completion;
explicit requests after expiry and ambiguous legacy tombstones still count as
forgetting. No archive is connected yet. Next bind exact historical message,
canonical delivery evidence and outbound consent without extending execution or
silently ignoring derivative erasure. This does not replace the full goal.

ADR-0097 finds that delayed feedback depends on an approximately one-hour
executable copy, while expired vault plaintext was still readable before erasure
maintenance. The read boundary now denies before decryption, without extending
retention. Next separate short-lived permission from consented exact delivered
history and feedback/learning authority; do not call a CLI report delivery or
archive outbound data under inbound-only consent. Authenticated expiry metadata,
host-clock behavior and physical/derived-copy forgetting still need qualification.

ADR-0096 tracks the enlarged execution regression's genuine concurrency failure.
Two separately read discovery checkpoints can mistake another worker's completed
prefix for lost evidence. Controlled thread scheduling reproduces it before the
fix; a single per-iteration checkpoint now supplies both completion and cursor,
while real missing replay still rejects execution. Stress counts/failed batches
are retained rather than excused by passing individual reruns. No model calls.

ADR-0095 joins exact expression confirmation, real kernel authorization/outbox and
actual Hermes command-handler execution against a disposable local fixture sink.
Success/reject/partial/skip preserve body and single-start behavior, without
turning source uncertainty into authority or CLI reports into delivery success.
The composed test exposes a managed-venv symlink defect in the test launcher;
lexical interpreter entries now preserve dependencies. Genuine user ingress,
host capability observation and external delivery/feedback remain unqualified.
No additional real model calls; totals remain 95 logical / 107 HTTP attempts.

ADR-0094 binds source review to exact final expression, current intent and actual
renderer, with expression-limited retention and no inherited draft approval or
delivery authority. Actual retained Chinese reviews both complete but still give
coarse positive reasons; attribution/materiality judgment remains unqualified.
The widened regression exposes old claim/facet fixtures omitting ADR-0091's source
presentation. Fixtures now cover the full candidate; coverage guards stay strict.
Cumulative actual calls: 95 logical / 107 observed async HTTP attempts.

ADR-0093 independently reviews both retained ADR-0092 drafts using actual Qwen3.5
calls, without regenerating them. Both report supported, but the bicycle review
collapses source-backed summary and model-originated suggestions. This does not
establish attribution fidelity or qualify admission. The expression itself also
needs source-aware assessment; do not confuse English draft review with Chinese
expression review. Preserve this ambiguity and test provenance boundaries rather
than stack word-specific rules or assume a longer diagnostic prompt is superior.
Cumulative actual calls: 93 logical / 105 observed async HTTP attempts.

ADR-0092 composes two fresh actual interpretation-selection-expression-review
chains. Both select shares; one fidelity review is shadow-eligible but explicitly
not safe for delivery, the other fails on a JSON code fence. Interpretation can
add source-absent practical details, and fidelity to a generated draft cannot
prove fidelity to sources. Next compose/evaluate source support separately, not
tyre/video keyword rules. Shared bounded JSON transport normalization now accepts
one complete JSON fence without changing values or supplying missing fields;
original failures remain failures. This is not semantic qualification or fallback.

ADR-0088/0089 add source-linked reasoned abstention and explicit unassessed coverage,
not executable silence or preference learning. First replication has five valid
results and one invalid JSON failure; its history is retained. ADR-0090's fresh
three-context paired experiment structurally completes six calls but finds a
missing source URL and questionable conservative/pragmatic explanations. One
blinded Qwen diagnostic overlooks those concerns and fails strict parsing due to
a code fence; it is not a semantic admission gate. Canonical provenance now enters
expression independently of whether the drafting model remembered its URL.
ADR-0091 now also fixes provenance in newly minted original-draft contracts before
selection/confirmation, preserving original wording and historical contract policies.
Typed channel capacity and separate wording/source atoms avoid rejecting ordinary
valid long provenance. Historical pending contracts/lifecycle remain unqualified.
Next qualify
per-decision/source semantics and the useful end-to-end path, not just formatting.

ADR-0084/0085 record actual feedback interpretations, a failed initial contract
and bounded model recovery without automatic learning permission. ADR-0086's
different-family review finds three interpretations acceptable, but warns about
permission versus enthusiasm and temporary availability versus lasting preference.
This is diagnostic evidence, not semantic ground truth or qualified usefulness.

The existing learned-advice bridge dropped encrypted rationale while transmitting
polarity/masses. It now carries canonical source-linked notes with qualifications
and unchanged weights/authority. ADR-0087's first matched ablation does not establish
improvement: two pairs return empty proposals; the third has similar raw drafts,
with an acceptance difference caused by a 143-character reason exceeding the old
128-character adapter cap. Aligned that cap with the domain's 512-character limit
and distinguish model silence from parser rejection. Next use fresh meaningful
opportunities with matched explicit baseline context and controls, not winning
sample selection; then qualify tentative feedback integration and longitudinal benefit.
The same paired audit also found scenario names leaking into subject IDs and URLs;
matched arms alone are insufficient. New paired inputs use opaque identifiers,
but prior feedback/reviewer fixtures need their own blinding audit before semantic
qualification. Preserve those results with limitations, not as clean blind evidence.
This does not supersede the expression/source-support or real host-chain gates.

### Prior finding: independence does not establish source support

ADR-0072 records a real different-family reviewer accepting the retained draft's
unsupported zero-loss guarantee. Source-support review exists in bounded shadow
mode, but is not semantically qualified and does not authorize delivery. Preserve
the miss and calibrate claim/evidence reasoning on fresh diverse cases, not a
phrase blacklist or a regenerated cleaner draft. Recorded source timing and an
atomic start-insertion fence now strengthen the review contract, not its judgment.

ADR-0073 adds an important correction: a paired method comparison explicitly
examined that closing and still interpreted it pragmatically as a suggestion.
Thus it is not established that the model merely skipped it, or that our authored
negative label is independently correct. Eight broad diagnostic cases matched
expectations, but the paired study did not show method superiority. Baseline stays
the runtime default; do not accumulate ineffective prompts or relabel to pass.
Next separate material verifiable claims from tentative/conversational content
and audit extraction coverage and labels before relying on support verdicts.

ADR-0074 adds opt-in inspectable unit/quotation accounting. Its actual retained
candidate review passed lexical coverage, but the model classified a compound
advisory/factual ending only by primary function. Material-assertion extraction
remains unproven; no support gate is qualified. The same turn repaired a reproduced
expression-window defect: unrelated higher-priority discovery could otherwise
displace a valid original source and silently block the selected intent.

### Prior finding: evidence lifetime through selection

ADR-0065 records a reproduced gap: withdrawal of an explicit profile during
model selection did not invalidate the retained frame. Generated candidates now
revalidate their original discovery/profile evidence before frame creation and
at selector call/return boundaries. This preserves useful positive selection,
not blanket silence. The source-epoch regression covers eight synthetic cases;
this is not production, dispatch, natural-expression or human-usefulness proof.
Further real-model calls are authorized without a total-count cap, within the
unchanged isolated synthetic/public-only, no-send, no-production-change scope.

Current phase: Phase 5 — faculty migration in bounded shadow mode

Next critical path (revisit after evidence, not a frozen design): calibrate semantic
and source-entailment review for the now-bound selected draft; admit an eligible
expression through current user policy and dispatch; observe useful, authorized
outcomes and learn from them. Selected-opportunity binding and style composition
exist in shadow, not a qualified production loop. Guard regressions
are necessary, but cannot substitute for this useful end-to-end behavior or the
current-installation, lifecycle, migration and production canary gates below.

Working branch: `feat/alive-kernel-3`

This is a living engineering contract, not a frozen specification. It records
why Hermes Alive exists, what we currently believe, what evidence changed our
mind, and which production gates remain. Update it whenever implementation or
evaluation disproves an assumption. A change is welcome when it moves the
project closer to the North Star and preserves the invariants below.

## North Star

Hermes Alive should make Hermes a continuous, attentive and self-correcting
assistant rather than a timer that periodically generates messages.

An Alive action should arise from a traceable chain:

```text
experience -> interpretation -> memory/belief -> intent -> decision
           -> authorized action -> outcome -> reflection/learning
```

“Alive” does not claim consciousness or imitate biological needs. It means:

- continuity across turns, restarts and model changes;
- a coherent history of experiences and commitments;
- context-sensitive initiative, including the ability to remain silent;
- learning from attributable outcomes rather than invented emotion;
- explicit uncertainty, provenance and reversible memory;
- behavior that stays under the user's authority.

## Invariants

These may be refined, but must not be silently weakened.

1. **User sovereignty** — the user can inspect, correct, forget, pause and
   bound proactive behavior. Silence never incurs a social penalty.
2. **Traceability** — every external action has an event, intent, policy
   decision, authority basis and outcome.
3. **Epistemic integrity** — observation, inference, preference, commitment
   and fiction are different data types. Confidence is not evidence.
4. **Safe silence** — uncertainty, corrupt state or missing authority fails
   closed for proactive external action, not for critical system notices.
5. **Channel and model neutrality** — Hermes owns providers and delivery
   platforms. Alive consumes capabilities; it does not hard-code a provider or
   Weixin as its identity.
6. **Independent plugins** — other plugins may publish standard events, but
   Alive cannot require or reach into their private state.
7. **Durable semantics** — retries are idempotent; acknowledged delivery is
   distinct from attempted delivery; restart cannot invent or duplicate work.
8. **Reversible evolution** — migrations, learned state and policy changes
   have versioning, audit evidence and rollback paths.
9. **Bounded autonomy** — models may propose and deliberate. Deterministic
   authority, privacy, rate and risk boundaries remain outside model control.
10. **No theatrical metrics** — human-like language is allowed, but arbitrary
    `affection`, `annoyance` or “sleep” numbers cannot masquerade as facts.

## Current diagnosis (2.9.8)

What is worth preserving:

- send-time context rechecks and interruption restraint;
- acknowledged delivery semantics and topic reservations;
- discovery diversity, novelty and provenance work;
- bounded interest/voice adaptation;
- lifecycle, portability, rollback and extensive regression tests;
- explicit shadow/enforce modes.

What must change:

- a polling pipeline currently substitutes for persistent intention;
- experience is split across unrelated JSON/JSONL files;
- the 3,000-line watcher owns scheduling, cognition, policy and execution;
- mood is produced by hand-tuned arithmetic and can punish non-response;
- dream consolidation can turn model confidence into direct memory mutation;
- there is no first-class agenda, commitment ledger or outcome-learning loop;
- tests prove many rules, but not longitudinal usefulness or coherence.

## Target kernel

```text
Hermes and plugin events
        |
        v
Durable Experience Journal  ---> privacy/redaction boundary
        |
        v
Typed Memory and Belief Store <--- contradiction + expiry + correction
        |
        v
Opportunity Generators ---> Persistent Agenda / Commitments
        |                         |
        +------------+------------+
                     v
       Deliberation (value, urgency, novelty,
       confidence, interruption cost and risk)
                     |
                     v
       Deterministic authority and safety gate
                     |
                     v
          Hermes capability / channel action
                     |
                     v
             Outcome and reflection
```

The kernel is intentionally small. Discovery, Circadian, voice, weather and
future faculties become adapters or opportunity generators, not owners of the
main loop.

## Delivery phases and exit gates

### Phase 0 — Baseline and preservation

- [x] Record the North Star and invariants.
- [x] Preserve the working 2.9.8 behavior on a separate branch.
- [ ] Capture a replay corpus from sanitized historical events.
  - [x] Read-only content-free current-log pilot with per-export pseudonyms and
    explicitly unknown outcome labels (ADR-0053); private data stays outside Git.
    This does not close rotated-history coverage, human calibration or causal
    decision replay, and must not be scored as useful/confirmed delivery.
- [ ] Define longitudinal quality and interruption metrics.

Exit: old behavior can be replayed and scored without sending messages.

### Phase 1 — Durable experience journal

- [x] Define a typed event envelope with causation and correlation identity.
- [x] Add an append-only SQLite journal with idempotent append.
- [x] Add integrity hashes and monotonic consumer checkpoints.
- [x] Add a first privacy boundary for structural lifecycle/session events;
  conversation content remains excluded until typed retention policy exists.
- [x] Add privacy-bounded structural adapters for official Hermes lifecycle,
  inbound/outbound turn and tool-round hooks, including persistent causal turn
  linkage and crash interruption facts (ADR-0013).
- [x] Add per-user, Hermes-authorized, expiry-bounded and erasable conversation
  content retention while keeping fresh installs structural-only (ADR-0014).
- [x] Add privacy-bounded native tool receipts. Treat ordinary prose-derived
  `ok/error` classifications as `outcome=unknown`; learn only from explicit
  executor terminal facts until Hermes exposes effect proof (ADR-0015).
- [x] Add opt-in shadow mirroring that cannot influence legacy decisions.

Exit: restart/replay reconstructs the same ordered experience stream, duplicate
ingestion is harmless, and no secret-bearing payload crosses ingestion policy.

### Phase 2 — Typed memory and beliefs

- [x] Define memory kinds, authority classes, lifecycle states and admission
  principles; see `adr/0002-typed-memory-is-a-projection.md`.
- [x] Implement episodic, semantic, preference, commitment and self-model
  records with provenance, confidence, validity, sensitivity and supersession.
- [x] Retrieve by relevance, importance, recency and authority without losing
  provenance; BM25 + explainable RRF is the deterministic baseline (ADR-0005).
- [ ] Make correction, forgetting and privacy erasure propagate predictably
  (encrypted content-vault primitive and resumable managed-backup purge pass;
  reference-only memory events and replay-safe item/subject forgetting pass;
  WSL, lifecycle and operator-control proof remain).
- [x] Retire direct Dream mutation and replace it with separately consented,
  evidence-bound, expiring memory proposals that require explicit user review
  before activation (ADR-0016).
- [x] Add a provider-neutral synthesis boundary that uses Hermes model routing,
  independently validates candidates, records actual-model attribution and
  persists no raw prompt/response (ADR-0018). Automated invocation remains
  shadow/off until longitudinal quality evidence exists.

Exit: every retrieved memory explains why it exists; contradictions and user
corrections are represented rather than overwritten.

### Phase 3 — Agenda, intentions and deliberation

- [x] Add durable commitments and opportunity records (ADR-0006; shadow-only
  authority, lifecycle, encrypted content and replay baseline implemented).
- [x] Generate multiple typed candidate actions, including deliberate silence;
  candidate sets and their encrypted explanations now replay durably.
- [x] Evaluate user value, urgency, novelty, confidence, interruption cost,
  risk and authority separately without an opaque weighted score (ADR-0007).
- [x] Let the model deliberate within structured bounds; keep policy external.
  Frames, rationales, policy rejections and validated choices now have an
  encrypted, deterministic replay projection. A provider-neutral Hermes-routed
  selector now exists behind an unscheduled, non-executing boundary (ADR-0021).
- [x] Join candidate framing, active-agenda validation, exploration and a
  durable selection in one crash-safe coordinator that always closes with
  deterministic silence and has no model/channel/tool side effects (ADR-0020).
  - ADR-0061 separates idempotent preparation from explicit audit silence and
    opt-in model deliberation. The latter composes the existing selector without
    action execution; event-to-candidate interpretation and live orchestration
    are not complete merely because this internal composition passes.
- [x] Separate selected intent from send-time authority. Short-lived structural
  permits now recheck latest state, current policy, active user authority,
  evidence and the exact Hermes capability without executing (ADR-0022).
- [x] Require every durable action attempt to consume an unexpired matching
  authorization receipt, with latest-state rechecks and dependency-ordered
  crash recovery (ADR-0023). No executor is connected.
- [x] Materialize authorized attempts into a deadline-bounded leased outbox;
  prove concurrent claim exclusion, stale-token rejection, crash recovery,
  authenticated result reconciliation and no-redelivery recovery (ADR-0024).
- [x] Replace caller-supplied execution policy with user-owned, revisioned,
  replayable autonomy state; bind authorization and dispatch to its exact
  version so pause and policy changes revoke queued work (ADR-0025).
- [x] Distinguish leased, externally started and uncertain dispatch so a crash
  at the adapter boundary can neither duplicate nor falsely claim an action.
  Terminal results bind the exact start generation, and v2 leases migrate
  conservatively to uncertainty (ADR-0026).
- [x] Replace arbitrary candidate JSON at the execution boundary with a
  versioned, destination-free action contract. Bind it cryptographically into
  authority, attempt validation and dispatch (ADR-0027).
- [x] Bind authorization and dispatch to an authenticated snapshot of actual
  Hermes host capabilities plus a separately encrypted, user-authorized route.
  Request acceptance is not delivery evidence, so the live bridge remains
  disconnected while the stable public plugin API lacks terminal delivery
  receipts (ADR-0028).
- [x] Replace per-acquisition full-history evidence scans with a rebuildable,
  transactionally checkpointed projection. Batch size bounds transaction cost,
  never history correctness; journal facts are re-authenticated on use
  (ADR-0029).
- [ ] Run the new decision engine in shadow against production events.

Exit: every proposed action has a stable reason and every rejection is
inspectable; replay is deterministic outside explicitly recorded model calls.

### Phase 4 — Outcomes, reflection and learning

- [x] Harden new user-outcome admission with exact attempt attribution and
  host-recorded explicit operation kinds (ADR-0041).
- [x] Revalidate user attribution in legacy outcome, reflection and preference
  reads, including source expiry (ADR-0042/0043).
- [x] Bind generic delivery/task admission and cached/dependent evidence reads
  to canonical signed dispatch chains (ADR-0044/0045).
- [x] Revalidate factual evaluation labels, sequence/clock snapshots, user
  benefit versus operational completion and prediction evidence scope/lifetime
  (ADR-0046..0049; synthetic shadow proof, not human qualification).
- [ ] Audit remaining projection integrity, duplicate result observations and
  operational host-clock reconciliation behavior before activation.
  - [x] Exclude signed receipt aliases from outcome admission and dependent
    cached reads, and validate before limiting exposure history (ADR-0051).
  - [ ] Qualify arbitrary cache repair/deletion, multi-generation/conflicting
    outcomes and large-history performance; alias exclusion is not full proof.

- [x] Link action attempts and evidence-backed delivery, reply, correction,
  feedback and downstream task outcomes to validated selections (ADR-0008).
- [x] Learn timing, topic, presentation and interruption estimates from bounded,
  expiring, retractable reviewed evidence without overriding explicit memory
  preferences (ADR-0010).
- [x] Treat no reply as ambiguous, never as punishment evidence; absence is
  intentionally not representable as an outcome kind.
- [x] Store reflections as evidence-backed proposals with bounded expiry,
  explicit user review and retractable acceptance (ADR-0009).
- [x] Add constrained exploration budgets, delivered-exposure history and
  topic/source anti-echo-chamber gates that can only narrow base policy
  (ADR-0011).
- [x] Add time-separated factual replay evaluation that rejects future
  evidence, preserves unknown feedback and forbids unsupported counterfactual
  policy claims (ADR-0012).
- [x] Define complete blinded-review metrics and a minimum qualification gate
  for memory consolidation: false-memory classes, durable-claim recall,
  citation accuracy, safe silence, duplication and review burden remain
  separate measures (ADR-0019). The checked-in corpus is synthetic machinery
  proof, not longitudinal product evidence.

Exit: learning improves held-out replay metrics without increasing interruption,
factual error or user-control violations.

### Phase 5 — Faculty migration

- [x] Port external Discovery through a typed opportunity-only ingestion
  boundary with encrypted evidence, material-update supersession and a
  dual-opt-in no-send shadow bridge (ADR-0030). Local filesystem discovery
  remains deliberately outside this completed external-source slice.
- [ ] Split user availability from optional character-like Circadian styling:
  - [x] add a replayable, fail-closed availability projection where direct
    activity can block but absence cannot grant permission (ADR-0031);
  - [x] add a dual-opt-in one-way shadow bridge from the legacy activity guard;
  - [ ] remove Circadian phase as live interruption authority after shadow
    comparison and retain it, if useful, only as presentation rhythm.
- [ ] Port voice as presentation policy, not a truth source:
  - [x] add a replayable explicit-preference projection with deterministic
    neutral defaults and advisory-only inferred/legacy state (ADR-0032);
  - [x] add a dual-opt-in one-way legacy voice shadow bridge;
  - [x] add encrypted meaning atoms, a provably lossless deterministic
    renderer and fail-closed classification for free model output (ADR-0034);
  - [x] define an independent semantic-review contract, explicit failure
    taxonomy and complete multilingual adversarial replay metrics (ADR-0035);
  - [x] add owner-scoped typed inspect/withdraw/correct controls with durable
    successor recovery and downstream receipt invalidation (ADR-0038/0039);
  - [x] make semantic message history discoverable with owner-filtered,
    bounded pagination and revalidated preview states (ADR-0040);
  - [ ] build a qualification-sized human-calibrated corpus and live
    user-control integration;
  - [ ] replace the legacy live voice consumer only after shadow qualification.
- [ ] Replace heuristic mood with explainable dispositions:
  - [x] define authenticated post-selection expression cues that retain each
    independent dimension's evidence and grant no decision authority
    (ADR-0033);
  - [x] add the meaning-first deterministic fidelity baseline (ADR-0034);
  - [x] persist encrypted model candidates and authenticated review receipts
    with selection/erasure/expiry invalidation (ADR-0036);
  - [x] connect an unscheduled provider-neutral model-rendering shadow
    comparator to the ADR-0035/0036 contracts with bounded calls and durable
    failure accounting (ADR-0037);
  - [ ] run real-provider replay with verified model-family mappings and
    human-calibrated judgments;
  - [ ] remove legacy mood, relationship and `social_urge` influence only
    after replay and canary qualification.
- [ ] Retire the monolithic watcher after parity and rollback drills.

Exit: legacy runtime can be disabled with feature parity, improved evaluation
and a one-command rollback.

### Phase 6 — Production qualification

- [ ] Fresh install, upgrade, uninstall/reinstall and data migration matrices.
  - [ ] Confirm runtime interpreter dependency preparation, including the
    `tzdata>=2025.2` warning observed in the isolated production image on
    2026-10-12. Declared dependencies and a successful hook load are not proof
    of a correct from-zero installation.
    - ADR-0050: declared dependencies were subsequently admitted on inspected
      official snapshot `f925b017` in disposable NAS/Linux Docker. Same-revision
      refresh plus package/runtime uninstall-reinstall preserved real synthetic
      journal, checkpoints, keys and encrypted content. This is a bounded pass,
      not today's latest commit, published GitHub transport, earlier-release
      upgrade or full platform qualification. See `INSTALL_ADMISSION_20261012.md`.
  - [x] Bounded public-baseline revision upgrade and dormant rollback/re-upgrade
    on the inspected official source snapshot, preserving synthetic legacy
    configuration and encrypted kernel state (`UPGRADE_ROLLBACK_20261012.md`).
    This does not close the full matrix or prove live authorization continuity.
- [ ] Linux, Windows, WSL and Docker/NAS lifecycle verification.
- [ ] Provider and channel substitution tests owned by Hermes capabilities.
- [ ] Crash, duplicate event, partial send and corrupt-state fault injection.
- [ ] Longitudinal shadow evaluation followed by bounded live canary.
- [ ] User-facing inspect/correct/forget/pause controls.

Exit: controlled production canary passes, rollback is proven, and the user
accepts the observed long-term behavior rather than only isolated messages.

## Quality measures

Track trends and distributions, not a single synthetic “alive score”.

- useful proactive outcome rate;
- interruption regret and immediate-dismissal rate;
- unsupported factual claim rate;
- commitment completion and stale-commitment rate;
- duplicate topic/action rate;
- memory provenance and correction accuracy;
- silence quality (messages correctly not sent);
- restart/replay divergence;
- policy-denied and authority-ambiguous actions;
- user inspection, correction and disable friction;
- latency, model calls, token cost and storage growth.

## Assumption register

| ID | Current hypothesis | How it can be disproved | Status |
|---|---|---|---|
| H1 | An append-only local journal is sufficient before adopting a distributed workflow engine. | Multi-process/device recovery cannot be made correct with SQLite leases and idempotency. | Active |
| H2 | Existing faculties can migrate behind event/opportunity interfaces without a big-bang rewrite. | Shadow parity requires preserving watcher-internal coupling. | Active |
| H3 | Explainable dispositions outperform hand-authored pseudo-emotions in longitudinal coherence. | Blinded replay and live feedback show lower naturalness without safety gain. | Active |
| H4 | Model deliberation plus deterministic authority gates gives better initiative than either rules or a model alone. | Shadow evaluation shows no useful gain or unacceptable variance/cost. | Active |
| H5 | Other Hermes plugins can remain independent while publishing optional standard events. | Hermes lacks a stable event/capability boundary and adapters become private coupling. | Active |
| H6 | A portable local content vault plus coordinated managed-backup retention can give an honest, useful forgetting boundary without claiming control over arbitrary external copies. | Recovery drills cannot reconcile deletion with useful backups, or operators routinely bypass the managed boundary. | Active |

## Decision and revision protocol

For each material change:

1. reread the North Star and invariants;
2. state the hypothesis and observable success/failure criteria;
3. add or amend an ADR for structural choices;
4. implement behind a versioned or shadow boundary;
5. test replay, faults, privacy, migration and rollback;
6. record evidence, surprises and rejected approaches;
7. update this plan, including changes of direction;
8. do not equate code presence with runtime correctness.

## Change log

### 2026-10-12 — First real multilingual reviewer evidence

- Ran all 12 distinct public seed cases through the inherited Hermes route
  in the production image with a disposable profile. Actual responses were
  `custom:ustc / deepseek-flash`: 3/3 faithful controls accepted, 0/9 risky
  cases accepted, all nine focal risks found.
- Actual output exposed incomplete seed labels. Marked their scope explicitly
  and withheld issue precision; overlapping classifications require exhaustive
  human judgments before they can be called false positives.
- Added an opt-in replay runner with saved-batch rescoring, exact-cohort
  accounting, failed-case retention and explicit nonqualification reporting.
- A second requested selector returned permission denial for 3/3 controls.
  Independent full-pair execution remains unverified; production model
  configuration was not changed. See `SEMANTIC_REPLAY_20261012.md` and evidence.

### 2026-10-12 — Executable bounded shadow comparator

- Connected deterministic baseline, natural model rendering, encrypted
  candidate persistence and independent review in a two-call operation
  (ADR-0037). Hermes retains provider selection and fallback responsibility.
- Inspected the supported auxiliary interface and used actual response model
  plus host route metadata; unknown independence domains fail visibly.
- Added durable start/failure accounting, bounded calls, strict review parsing
  and cancellation propagation. Repeated operation IDs cannot spend again.
- Injected execution verified provider errors, timeout, missing route metadata,
  malformed JSON, same-model review and intent changes during an async call.
- Real-provider quality calibration remains unfinished; no production scheduler
  consumes this comparator yet.

### 2026-10-12 — Revalidated semantic-review receipts

- Added encrypted persistence for free model candidates; the journal retains
  only a content reference, digest, renderer provenance, changed atom IDs and
  explicit authority nonclaims (ADR-0036).
- Added authenticated structural review receipts bound to the exact candidate
  event, selection, reviewer execution/model/domain and complete atom findings.
- Every read now decrypts and re-hashes content, reruns deterministic and
  independent checks, confirms the bound selection is still latest and checks
  current expiry. A signature alone is deliberately insufficient.
- Verified fail-closed invalidation after superseding intent, candidate erasure,
  renderer-evidence mismatch and expiry. Raw candidate text and review prose
  never enter the experience journal.
- The store remains shadow-only and performs no provider call or delivery.

### 2026-10-12 — Independent semantic review and adversarial replay

- Corrected an over-conservative baseline: ordinary paraphrases now require
  review instead of failing merely because they do not contain the entire
  source sentence. Missing protected dates, amounts, links, contacts,
  negation or uncertainty markers still fails closed.
- Added an exact candidate-digest review contract with complete per-atom,
  added-claim, speech-act and protected-literal findings (ADR-0035).
- Required distinct renderer/reviewer executions, actual model identities and
  declared independence domains. Self-review is invalid, not weak evidence.
- Kept a clean independent result shadow-only: it grants no truth, action,
  route or delivery authority.
- Added complete-cohort metrics and a 12-case Chinese/English/Japanese
  adversarial seed covering faithful paraphrases plus nine distinct semantic
  failure classes. The seed is explicitly machinery proof, not product
  qualification; at least 100 blinded, human-calibrated cases remain required.

### 2026-10-12 — Presentation policy boundary

- Audited the legacy voice path and found that it combined prose style with
  guessed relationship stage, ignored-message counters and `social_urge`.
  Ordinary replies, silence, night activity and lexical heuristics could
  durably mutate the same state consumed by composition.
- Added an authenticated, replayable presentation projection (ADR-0032).
  Only causally proven explicit user preferences affect its resolved plan;
  accepted-learning and legacy signals remain expiring advisory evidence.
- Added deterministic neutral defaults and fail-neutral corruption behavior.
  The plan cannot grant action/route authority or permit semantic changes.
- Added a dual-opt-in one-way legacy bridge. It stores pseudonymous subjects
  and numeric dimensions only, and the production watcher never reads back
  the shadow result.
- Current research/product evidence supports separating controllable style
  from capability and safety, while warning that implicit personalization can
  change safety and utility. This strengthens the requirement for explicit
  provenance and independent semantic-fidelity evaluation.

### 2026-10-12 — Explainable post-selection disposition

- Audited the legacy proactive disposition and confirmed it blends synthetic
  mood, relationship stage, social urge, non-response and personality into an
  opaque willingness score before the send decision.
- Reframed disposition as expression after a selection is independently
  validated (ADR-0033). Risk, interruption cost, urgency and grounded novelty
  produce separate evidence-carrying cues; there is no blended mood score.
- Silence and non-communication actions produce no renderable disposition.
  Every snapshot denies emotion/relationship claims, action authority,
  selection mutation and semantic change.
- Consumers must re-authenticate and recompute the snapshot from the latest
  validated selection. The new path is unscheduled and not connected to the
  production watcher.

### 2026-10-12 — Meaning-first semantic fidelity baseline

- Added encrypted, evidence-linked semantic atoms before style rendering
  (ADR-0034). Critical dates, amounts, links, contacts, uncertainty and
  negation require exact protected literals.
- Bound meaning to a strict reference-only deliberation candidate and then to
  the exact latest validated selection. A later validated intent invalidates
  the old render receipt even if the candidate identity is unchanged.
- Added a deterministic renderer that changes separators only and can prove
  exact transformation fidelity. It stores raw text only in the erasable
  content vault.
- Free model output cannot self-certify. Missing atoms/literals are rejected;
  otherwise it remains `review_required` because extra prose can introduce
  unsupported claims or shift relations.
- Clarified the proof boundary in code and events: rendering fidelity does not
  prove truth, evidence entailment, action authority or route authority.

### 2026-10-12 — Incremental dispatch evidence projection

- Removed the full-journal reverse scans from every outbox reconciliation and
  acquisition path.
- Added an atomic checkpoint plus a minimal index of authenticated start/result
  event identities. Projection runs to a captured watermark in bounded batches
  rather than applying a correctness-breaking look-back limit.
- Added concurrent projector, invalid-authenticator, incremental catch-up and
  discard-and-rebuild tests. Derived rows are installation-authenticated and a
  startup count/HMAC audit rebuilds logical corruption before leasing. Startup
  recovery reports evidence checkpoint progress before materializing dispatch
  state.

### 2026-10-11 — Host capability and route authority boundary

- Audited official Hermes `v0.21.6` at `f27cdbce`: the public plugin injection
  API schedules a turn but explicitly does not prove completion; adapter
  `SendResult` and the final-delivery ledger remain internal to the gateway.
- Added authenticated, versioned host capability snapshots with explicit
  receipt semantics. A private API or request-accepted-only interface cannot
  authorize proactive external delivery.
- Added encrypted route bindings requiring exact user authority. Journal state
  retains only structural references and a keyed route fingerprint; route
  plaintext stays in the erasable vault.
- Bound send-time authorization and dispatch start to the exact route and host
  snapshot. Host upgrades, route revocation, content erasure and receipt-level
  downgrade fail closed before external start.
- Kept production `v0.21.3` and the legacy watcher untouched. The new live
  bridge remains deliberately absent until a supported terminal-receipt API
  exists.

### 2026-10-09 — Kernel exploration begins

- Reframed Alive from proactive messaging to continuous experience, intention,
  authorized action and outcome learning.
- Chose an append-only local journal as the first substrate; see
  `adr/0001-durable-experience-journal.md`.
- Kept 2.9.8 behavior untouched while the kernel develops in shadow.
- The first Windows contract run exposed that SQLite transaction contexts do
  not close file handles. The journal now owns explicit connection closure;
  Windows file lifecycle remains a mandatory portability gate.
- Review found that a frozen envelope could still expose mutable nested payload
  values. Payloads are now recursively immutable and detached from caller-owned
  objects; concurrent duplicate ingestion is a required idempotency contract.
- Added an installation-local HMAC identity boundary. Initial shadow ingestion
  records hook structure and pseudonymous linkage, never raw message content,
  credentials or external platform IDs. It defaults off until deployment
  acceptance explicitly enables it.
- Defined typed memory as a replayable projection. Model confidence is now
  explicitly rejected as a promotion authority; raw conversation ingestion
  remains blocked until real erasure semantics exist.
- Phase-1 journal/privacy contracts passed repeatedly on Windows and as part of
  the complete Linux suite. The full-scale Linux stress run also passed: 32
  concurrent safe-I/O workers, 6,000 interest deliveries, 4,000 feedback
  updates, 10,000 delivery plans, 10,000 policy evaluations, 2,000 watcher
  ticks, 20 lifecycle cycles and 50 injected failures, with zero file-descriptor
  or thread leakage. A Windows-only legacy test invocation exposed console GBK
  decoding in the existing location test harness; the same test passed under
  the authoritative Linux suite and is not attributed to the kernel change.

### 2026-10-09 — Typed memory projection begins

- Implemented idempotent memory projection in the same transactional store as
  the experience journal, with explicit kind, authority, state, validity,
  sensitivity, provenance and transition history.
- A confidence-1.0 model inference remains `proposed`; only admitted authority
  can activate it. Direct observations cannot activate inferred preferences.
- Contradictory evidence contests both claims instead of overwriting either.
  An explicit user correction can supersede a live matching target, but cannot
  reuse an already superseded target to create parallel active truths.
- Retrieval now requires an explicit sensitivity clearance. Projection state
  can be discarded and deterministically rebuilt from journal history.
- Implementation review changed correction ordering: explicit supersession is
  processed before same-value deduplication so user authority is not erased by
  a prior contested observation.
- The typed-memory contracts passed repeated Windows runs and the complete
  Linux regression/matrix/scaled-stress suite, including concurrent projection,
  discard-and-rebuild replay, lifecycle rollback and failure injection. The
  kernel remains shadow-only and has not ingested production conversation data.
- The first memory prototype exposed a deliberate boundary problem: private
  values embedded in an append-only event cannot be genuinely forgotten.
  ADR-0003 therefore proposes a durable metadata journal plus a separately
  erasable content vault. Production plaintext ingestion remains blocked until
  WAL, backup and interrupted-erasure tests prove the selected design.

### 2026-10-10 — Erasable content boundary prototype

- Inspected Hermes 0.21.3's real vault implementations before choosing a
  design. The built-in Fernet login vault and interactive 1Password/Bitwarden
  backends do not provide an arbitrary, headless content-erasure contract, so
  Alive does not pretend they do.
- Added an AES-GCM content vault that stores only authenticated ciphertext and
  metadata, returns opaque journal-safe references, audits resolution, enforces
  retention deadlines and records durable tombstones.
- Erasure now survives interruption: live ciphertext deletion, WAL truncation,
  compaction and affected managed-backup purge resume on next open. Unmanaged
  disk images are explicitly outside the claim; this is an honest threat-model
  boundary rather than a promise software cannot keep.
- A Windows concurrency test found that simultaneous first-open WAL setup
  could leak a failed SQLite handle. Initialization now retries the transient
  lock and closes every failed handle. Thread/process first-use and concurrent
  backup/erase races are covered. Repeated Windows runs, Linux host, the actual
  Hermes NAS container, and the full Linux regression/matrix/stress suite
  passed.
- Production plaintext ingestion remained disabled while the next phase moved
  proposal values behind content references and defined explicit erased-state
  replay semantics.

### 2026-10-10 — Private memory leaves durable history

- Replaced persisted memory values with opaque encrypted-content references;
  neither `memory.proposed` nor `memory_records_v2` carries plaintext.
- Replaced plain value SHA-256 with an installation-keyed HMAC after threat
  review showed that cities, languages and booleans could otherwise be
  dictionary-enumerated from the journal.
- Made forgetting a durable, replayed event with exact target snapshots.
  Subject replay therefore erases only memories that existed when the user
  requested it, never later memories for the same person.
- Added one-to-many logical-memory/content associations so deduplicated
  proposals cannot leave orphaned private copies behind.
- Retrieval by ID now requires the same explicit sensitivity clearance as set
  retrieval. Missing, corrupted and erased content is typed and excluded from
  normal recall rather than fabricated.
- Repeated/concurrent append, cross-subject substitution, crash continuation,
  item/subject erasure and discard-and-rebuild pass on Windows, Linux and the
  actual Hermes Docker runtime. Production ingestion remains disabled pending
  WSL, lifecycle/doctor and operator-control gates.

### 2026-10-10 — Explainable recall baseline

- Added authorization-first memory search using BM25 and Reciprocal Rank
  Fusion over independent relevance, importance, recency and authority lists.
  This replaces a tempting but opaque hand-weighted “memory score.”
- Each result exposes matched terms, component ranks and the original source
  event IDs. A query cannot admit an unrelated memory merely because it is
  newer or marked important.
- CJK bigrams avoid the false matches produced by common single characters;
  no-match queries return silence rather than the least-bad memory.
- Semantic embeddings remain an optional future Hermes capability: private
  memory will not be silently exported to whichever model happens to be
  configured.
- Review of duplicate evidence found and fixed a privacy escalation bug: the
  logical memory now inherits the strictest sensitivity seen across equal
  claims, never the first/least restrictive label. Its primary reference also
  moves to ciphertext authenticated at that stricter sensitivity.
- Projection decisions, record timestamps and transitions now derive from the
  durable event clock rather than replay wall time. Rebuild tests compare
  timestamps as well as rankings, preventing recency drift after recovery.

### 2026-10-10 — Durable agenda baseline

- Added separate commitment and opportunity records instead of treating every
  interesting signal as a task or every task as ordinary memory (ADR-0006).
- Model and observation authorities may propose a commitment but cannot
  activate one. User-authorized transitions must cite a matching durable
  inbound event; a caller-provided authority label alone is insufficient.
- Agenda content uses the same encrypted, erasable vault boundary as memory.
  Deadlines, availability, provenance and lifecycle remain structural events.
- Snooze, completion, dismissal and expiry are distinct replayable states.
  Proposal retries are semantically idempotent despite fresh wall-clock values.
- The agenda remains shadow-only and performs no scheduling, policy decision,
  delivery or other external action.

### 2026-10-10 — Policy-bounded deliberation baseline

- Replaced the idea of one opaque “proactivity score” with independently
  evidenced value, urgency, novelty, confidence, interruption-cost, risk and
  authority assessments (ADR-0007).
- Every frame has exactly one deterministic silence candidate. Hard policy
  filters run before a model can choose, and selection is checked again after
  the model response.
- Candidate content, assessment reasons and model rationale live in the
  encrypted erasable vault. Structural journal events retain IDs, policy
  outcomes and causal links without private prose.
- Frame loading recomputes policy, verifies every cited evidence event and
  resolves every candidate content reference. Dangling evidence cannot appear
  as an auditable reason.
- Accepted and rejected selections survive discard-and-rebuild identically.
  No provider is called and no selected action is executed in this phase.

### 2026-10-10 — Evidence-backed outcome baseline

- Added an explicit action-attempt boundary between model selection and an
  external effect. Attempts carry stable idempotency keys but do not execute
  channel or tool operations themselves (ADR-0008).
- Delivery receipts, user replies/corrections/dismissals, explicit feedback and
  downstream task completion/failure require compatible source events that
  occur after the attempt and match its subject.
- `no_reply` is intentionally absent from the outcome vocabulary. Time passing
  cannot silently become rejection, negative reward or a social penalty.
- Private outcome detail is encrypted and erasable. Erasure preserves the
  structural fact and replay result while returning an explicit erased status.
- The result ledger remains shadow-only; no production delivery is attempted.

### 2026-10-10 — Reviewable reflection baseline

- Reflections are now expiring hypotheses rather than direct memory mutations
  or invisible prompt edits (ADR-0009).
- Delivery receipts and ordinary replies cannot support a reflection. Model
  synthesis requires explicit correction/dismissal/feedback or repeated task
  outcomes from independent attempts.
- Every proposal points to real outcome rows and the corresponding causal event.
  A historical user message from before the proposal cannot approve it.
- Acceptance, rejection and later retraction require matching user inbound
  evidence. Even accepted reflections do not automatically alter memory,
  thresholds or delivery policy.
- Encrypted reflection prose can be erased while its proposal/review history
  remains deterministic and visibly marked as erased.

### 2026-10-10 — Conservative preference-estimation baseline

- Kept explicit preferences in the typed-memory authority model and introduced
  a separate advisory estimator for weak learned patterns (ADR-0010).
- Only explicit feedback outcomes and currently accepted reflections can create
  learning signals. Delivery success, ordinary replies, model opinion and
  non-response cannot enter the estimator.
- Each source contributes once, per-origin weight is capped, total evidence
  mass is bounded and every signal expires. Repetition therefore cannot turn a
  weak estimate into an authoritative rule.
- Preference targets and rationale remain encrypted; only a keyed digest enters
  structural history. A stricter source can never be projected at a lower
  sensitivity.
- Retracting a reflection removes its contribution immediately. Explicit user
  retraction removes a signal, and discard-and-rebuild reproduces the result.
- Estimates are shadow-only and are not yet consumed by live deliberation.

### 2026-10-10 — Constrained exploration baseline

- Added a second gate that can only narrow candidates already admitted by the
  main authority/risk/interruption policy; it can never rescue an unsafe action
  (ADR-0011).
- Exploration count, topic share, source share and same-topic streak have
  explicit rolling limits. Silence always remains admissible when diversity
  rejects every action.
- Only successful delivery receipts enter exposure history. Selection, attempt,
  failed delivery and no-response do not pretend that the user saw an item.
- Topic and source labels are encrypted; structural history accepts only keyed
  digests, preventing accidental plaintext metadata leakage.
- Gate results are recomputed on replay and stored as causal receipts. Every
  non-silence model selection must cite an earlier receipt that admits its exact
  candidate; direct bypass is rejected.
- The mechanism remains shadow-only and has not altered production discovery
  or delivery behavior.

### 2026-10-10 — Honest held-out replay baseline

- Added time-separated evaluation of predictions made before factual action
  attempts. Training state cannot cross the holdout boundary and cited evidence
  must precede the attempted action.
- No response and missing labels remain unknown. Conflicting positive and
  negative evidence is also unknown rather than silently averaged into a
  convenient reward.
- Calibration comparisons require the exact same executed-attempt cohort.
  Reports explicitly refuse to claim that an unexecuted action or a different
  selection policy would have performed better.
- This closes the measurement primitive, not the Phase-4 exit gate: a real
  sanitized corpus and longitudinal shadow results are still required.

### 2026-10-10 — Official Hermes structural event adapter

- Verified the current Hermes hook contract from its running source before
  expanding the adapter: lifecycle/session events plus agent start, step and
  end are official; their contexts contain raw private content. The contract
  was cross-checked against upstream `main` at `f925b017` as well as the running
  Hermes Agent 0.21.3 image, rather than assuming legacy compatibility.
- Added all official non-command lifecycle and agent events to the hook while
  keeping the legacy watcher behavior unchanged. The shadow boundary stores
  only local pseudonyms, bounded structural counts and content-presence flags.
- Added persistent start/step/end causation and deterministic retry identity.
  Concurrent duplicate starts collapse to one event, while the same text sent
  again after completion becomes a new turn.
- Gateway restart and unexpected turn replacement now append a durable
  interruption fact before clearing activity state. Raw messages, assistant
  responses, model/provider aliases, tool arguments and tool results remain
  absent from SQLite/WAL evidence.
- This does not yet claim semantic message ingestion or authoritative tool
  outcomes; those remain gated on retention controls and native typed receipts.

### 2026-10-10 — Explicit erasable content consent

- Added `/memory alive` controls on Hermes' own slash authorization path. The
  hook consumes only its `alive` sub-namespace and leaves ordinary `/memory`
  behavior untouched across every Hermes channel.
- Default retention is off per pseudonymous user. Explicit consent chooses
  inbound, outbound or both, with a one-to-365-day fixed expiry. A model event
  cannot grant or widen consent.
- Authorized hook text is encrypted in the erasable vault; journal events keep
  only opaque authenticated references, the consent event and an honest marker
  that the official hook may truncate at 500 characters. Tool arguments and
  results remain forbidden.
- `retain off` stops future capture without rewriting history. `forget` is a
  durable request/execution/completion workflow that deletes subject content
  and managed backups, resumes after interruption, and works even when kernel
  shadow decision capture is disabled.
- Windows and Linux tests prove default-off behavior, per-user authorization, model
  rejection, encrypted-at-rest capture, ordinary `/memory` pass-through,
  disable-versus-forget semantics, replay and crash-resumed erasure. The real
  Hermes container also discovered `command:memory`, intercepted only `alive`
  requests and left ordinary memory commands untouched.

### 2026-10-10 — Honest native tool receipts

- Registered Alive against Hermes' public `post_tool_call` plugin hook instead
  of scraping assistant text or the lossy gateway step summary.
- Receipts contain pseudonymous call coordinates, tool name, bounded duration
  and terminal classification only. Arguments, results and error messages are
  excluded, and the observer stays inert unless kernel shadow mode is enabled.
- Hermes' ordinary `ok` and `error/tool_error` labels currently depend on
  return-value inspection. They are retained only as reported diagnostics and
  mapped to `outcome=unknown`, never to success/failure learning evidence.
- Explicit policy blocks, cancellations, timeouts and exception-backed errors
  are typed, learning-eligible terminal facts (ADR-0015).
- A clean-container run initially used the system Python instead of Hermes'
  virtual environment and incorrectly concluded that cryptography was absent.
  The supported Hermes environment actually locks `cryptography==50.0.0` and
  already provides AES-GCM. A later isolated dependency-resolution run caught
  that the resulting `>=50.0.2` declaration would force a host conflict. The
  plugin now matches the Hermes lock and still routes dependency consent
  through `hermes plugins install --yes-deps`.

### 2026-10-11 — Legacy Dream retirement and consented consolidation

- Source review disproved the legacy Dream documentation: the runtime did not
  merely save a diff for review. It read raw session transcripts without the
  new retention boundary and could directly mutate `MEMORY.md`, fact state and
  voice state from model output. The engine is now an inert compatibility
  tombstone; even a stale `HERMES_DREAM_ENABLED=1` cannot reactivate it.
- Separated permission to retain conversation content from permission to learn
  from it. Both default off per pseudonymous user. Retention alone never grants
  model interpretation, and learning consent without retained evidence has
  nothing to process.
- Added consolidation candidates limited to expiring fact, preference and
  self-model hypotheses. Every cited item must be decryptable retained content
  for the same subject; structural-only, erased, missing and cross-user evidence
  is rejected.
- Model output can create only an encrypted `proposed` memory. It cannot create
  commitments, delete, supersede, activate or silently alter policy. Explicit
  `/memory alive accept|reject|retract` review is the only activation path.
- Candidate IDs and command operation IDs are semantic idempotency keys;
  retries converge and changed reuse fails. Consent and memory projections can
  be discarded and deterministically rebuilt from the journal.
- This completes the safe consolidation primitive, not autonomous production
  learning. Candidate generation is not scheduled and production remains
  unchanged pending corpus evaluation and shadow qualification.
- The complete Windows run exposed a separate packaging defect: Python's
  `zoneinfo` has no system IANA database on ordinary Windows, while the plugin
  did not declare `tzdata`. The plugin now declares it explicitly so Circadian
  behavior survives a true fresh Windows install instead of depending on a
  developer machine's incidental packages. The same clean-image run confirmed
  that YAML parsing was also an undeclared runtime assumption, so `PyYAML` is
  now part of the plugin dependency contract rather than only CI setup.

### 2026-10-11 — Ordered crash recovery supervisor

- Added one startup recovery boundary for every implemented kernel projection
  instead of relying on whichever command or subsystem happens to run next.
- Recovery resumes erasure/expiry first, then advances consent, memory, agenda,
  deliberation, outcomes, reflection, preference and exploration in explicit
  dependency order (ADR-0017).
- Checkpoints advance in bounded batches and no-progress is a hard diagnostic.
  Repeated startup is a no-op after convergence; an interrupted run resumes
  from each projection's durable checkpoint.
- The supervisor is cross-process locked, creates no kernel store on a fresh
  install and has no channel, provider or tool side effects. Kernel recovery
  failure remains observable without preventing the legacy watcher startup.

### 2026-10-11 — Review-only model synthesis boundary

- Replaced the missing link between retained evidence and reviewable memory
  with a provider-neutral synthesizer rather than reviving Dream.
- Synthesis requires both retention and learning consent, consumes a bounded
  decryptable evidence window and delegates provider/fallback selection to
  Hermes' auxiliary model route.
- Strict JSON is only an interchange boundary: every candidate is validated
  independently, tied to in-window evidence and admitted solely as an
  encrypted, expiring proposal. Invalid siblings do not cancel valid ones.
- Actual response-model attribution is mandatory. Structural receipts contain
  no raw prompt, response or provider error text, and repeated operation IDs
  cannot trigger another model call.
- The callable remains unscheduled and cannot affect production behavior. The
  next evidence gate is a sanitized historical replay corpus with
  longitudinal usefulness, false-memory and review-burden metrics.

### 2026-10-11 — Honest consolidation evaluation gate

- Added complete blinded-review accounting instead of treating strict JSON as
  a quality signal. Every candidate and every zero-candidate case must be
  reviewed; incomplete cohorts are rejected.
- Durable claims have explicit case-local IDs. An acceptable candidate must
  match one ID and a claim cannot be counted twice, so recall cannot be entered
  as an unsupported aggregate number.
- Precision, recall, citation accuracy, sensitive/authority failures,
  duplication, safe silence and review burden are reported independently.
- A ten-case multilingual synthetic seed exercises the evaluator without
  containing historical user data. It explicitly does not close the Phase-0
  sanitized historical corpus or longitudinal evidence gates.

### 2026-10-11 — Subject authority boundary audit

- Pre-coordinator review found that agenda proposal sources were checked for
  existence but not subject ownership, and a caller-provided
  `USER_EXPLICIT` label could activate a commitment without proving the caller
  was that user. Proposal admission now proves both source scope and authority.
- Durable deliberation frames now reject foreign-subject evidence and reject
  missing, inactive or foreign agenda references. A valid active agenda item
  for the same subject is covered by an integration contract.
- This safety correction precedes the unified cognition-cycle coordinator;
  connecting components before fixing identity boundaries would have amplified
  the defect across the full action chain.

### 2026-10-11 — Integrated safe-silence cognition cycle

- Added a deterministic coordinator joining candidate frames, active agenda
  references, diversity annotations, the exploration gate and a durable
  selection in one idempotent cycle (ADR-0020).
- The coordinator deliberately selects silence even when an external action is
  admissible. This proves crash recovery, replay and audit structure without
  quietly turning integration work into production autonomy.
- Same-semantics retries add no journal events. Changed reuse fails closed, raw
  candidate content and diversity labels remain outside the structural SQLite
  history, and projection rebuild reconstructs the same gate and selection.

### 2026-10-11 — Gated provider-neutral intent selection

- Added an unscheduled selector that consumes only candidates admitted by both
  deterministic policy and the replayed exploration gate (ADR-0021).
- Provider choice and fallback remain Hermes responsibilities; receipts record
  the actual responding model, not the requested alias.
- Invalid JSON and forbidden IDs are contained before durable selection. Raw
  prompts, responses, rationales and provider errors do not enter the
  structural journal.
- A validated model choice still creates no action attempt and performs no
  channel/tool side effect. Replay and production shadow evidence remain
  required before it may be invoked automatically.

### 2026-10-11 — Short-lived send-time authority

- Added a non-executing authorizer between validated model intent and any
  future action attempt (ADR-0022).
- The boundary rechecks the latest selection and exploration gate, active
  agenda, current interruption/risk policy, evidence lifetime, subject,
  sensitivity and exact Hermes capability.
- Tightened authority provenance: an observed opportunity is not delegation,
  and an unrelated inbound message cannot be treated as confirmation.
- Authorized receipts expire within 60 seconds and are not revived by an
  idempotent retry. No production sender consumes these receipts yet.

### 2026-10-11 — Authorized attempts and causal recovery

- Removed the supported direct path from validated selection to action attempt;
  attempts now consume an exact, live ADR-0022 receipt (ADR-0023).
- Attempt projection independently rejects missing, expired, capability-
  mismatched and superseded authorization before any executor can act.
- Split recovery into deliberation-frame, exploration, deliberation-selection
  and outcome phases so empty projections reconstruct causal state in the same
  order as online admission.

### 2026-10-11 — Leased dispatch outbox

- Added a persistent outbox derived from authorized attempts (ADR-0024).
- Claims are transactional, generation-bound and short-lived; only the current
  holder can decrypt candidate content, release or acknowledge the row.
- Worker identity is pseudonymous and raw lease tokens never enter SQLite,
  journal events or logs.
- Authenticated terminal result events close the row and reconcile into normal
  outcome evidence. Losing the outbox after a successful transport cannot
  cause redelivery because reconstruction recognizes the signed result first.

### 2026-10-11 — Durable user autonomy policy

- Replaced ephemeral caller policy at authorization time with an authenticated,
  user-owned and revisioned projection (ADR-0025). No policy means disabled.
- Authorization, attempt admission and dispatch now retain the exact policy
  event. A newer policy or pause revokes pending and leased work; resuming never
  resurrects it.
- Concurrent same-revision updates select the earliest authenticated journal
  event, making online projection agree with deterministic replay.
- Review exposed the next required boundary: once a transport call begins, a
  pause cannot honestly recall it. Live adapters remain forbidden until a
  durable started/uncertain protocol closes that crash window.

### 2026-10-11 — Durable external-start boundary

- Added explicit `started` and `uncertain` dispatch states (ADR-0026).
- Candidate plaintext now crosses toward an adapter only through a one-shot
  execution grant after an authenticated structural start event is durable.
- Recovery and table-loss reconstruction never turn started work back into
  pending work. A valid late result bound to the start event and lease
  generation resolves uncertainty and projects the factual outcome.
- Added a conservative v2-to-v3 migration: an old leased row becomes uncertain
  and loses its worker/token fields rather than risking duplicate execution.
- The live Hermes capability bridge remains disconnected pending its own
  contract and provider/channel substitution tests.

### 2026-10-11 — Typed action contract and upstream capability audit

- Audited current upstream Hermes main rather than designing against the old
  production image. Public plugin injection proves request acceptance only;
  direct runner/adapter access is not a supported plugin boundary.
- Added a strict `hermes.channel.send` v1 document containing only bounded text
  and `plain|markdown` presentation. Any route, recipient, profile, thread,
  adapter or unknown field fails closed.
- Send-time authorization now binds an installation-keyed canonical action
  authenticator. Attempt and dispatch boundaries independently revalidate it
  before plaintext can cross.
- Deliberately left tool execution, internal review and live delivery
  disconnected until each has a real schema and trustworthy host receipt.

### 2026-10-12 — Private fallback preference clarified

- User-selected fallback for this installation is official DeepSeek
  (`provider=deepseek`, `model=deepseek-flash`), not `ustc/qwen3.6-chat`.
- Read-only production inspection confirmed this is already the configured
  `fallback_providers` route; no production configuration change or restart
  was necessary. Credential presence was checked without exposing its value.
- This is a private deployment preference, not a public installation default.
  Public model selection continues to inherit Hermes configuration.
- Provider redundancy does not establish independent semantic review when
  both routes use the same actual model family. Availability and review
  independence remain separate acceptance requirements.

### 2026-10-12 — Inspect and withdraw semantic content

- Added owner-scoped message inspection and durable withdrawal to `/memory
  alive`. Withdrawal invalidates deterministic renders, model candidates and
  review receipts on their next read, including after reopening the store.
- ADR-0038 separates withdrawal from encrypted-content erasure and platform
  recall. Previously delivered messages cannot be removed by this control.
- Focused tests exercise ownership, idempotency and downstream invalidation.
  Correction/replacement and discoverable identifiers remain pending; this is
  not a claim that all user-control or production gates have passed.

### 2026-10-12 — Crash-safe owner-authored correction

- Added a typed per-atom `correct-message` control and visible atom IDs.
  Corrections preserve provenance, unchanged atoms, sensitivity and expiry.
- ADR-0039 defines stable encrypted preparation, permanent old-version
  withdrawal and retryable successor definition. An old retry cannot revive a
  withdrawn successor; new content receives no inherited delivery authority.
- Added faults on both sides of withdrawal and checks for multi-line input,
  cross-user refusal, competing edits, successive edits and review invalidation.
- This completes a bounded typed correction baseline, not the entire natural
  feedback loop. Discoverable message history, live controls and qualification
  remain pending.

### 2026-10-12 — Discoverable owner message history

- Added `/memory alive messages` with newest-first, event-anchored pagination.
  SQL filters ownership/type before loading; a composite index bounds seeks
  without altering existing replay/checkpoints or rewriting journal events.
- ADR-0040 distinguishes content history from actual send/delivery evidence.
  Withdrawn, corrected, expired and unavailable records have no plaintext
  preview. Interrupted correction is explicitly different from completion.
- Tests exercise interleaved users, insertion-safe pagination, index use,
  invalid cursors/bounds, lifecycle states, erasure and anonymous refusal.
- Live user-control integration and feedback/outcome linkage remain pending.

### 2026-10-12 — User-outcome attribution defect found and narrowed

- Audit found that later same-user inbound events could be attached to any
  prior attempt, and ordinary replies upgraded through model-written details.
- New admission now requires exact attempt causation, consistent observation
  times and host-typed metadata for explicit feedback/correction/dismissal.
- ADR-0041 records the defect and regression proof without overclaiming:
  cached legacy outcomes, dependent learned state and transport/task attribution
  still need revalidation before live use. Production remains unchanged.

### 2026-10-12 — Cached outcome reads revalidated

- Outcome reads now bind materialized row identifiers to the original journal
  event and recheck current user-attribution rules. Invalid legacy rows are
  excluded without deleting historical evidence (ADR-0042).
- A regression injects an old-style misattributed cache row and proves it is
  absent from current reads while its journal event remains intact.
- Direct reflection/preference SQL reads remain a confirmed bypass requiring
  the next hardening step; this is not full learning-loop qualification.

### 2026-10-12 — Derived feedback projections revalidated

- Reflection admission/acceptance/reads and explicit/reflected preference
  admission/estimates now share stateless current user-attribution checks.
- Estimates bind cached signal identifiers, direction, weight and expiry to
  their original journal event, and reject expired source reflections.
- An integration regression emulates accepted and active legacy projections
  backed by unlinked feedback: invalid influence disappears without rebuild
  or history deletion. Altered cached weight is separately excluded.
- ADR-0043 retains open transport/task evidence and long-term usefulness
  qualification; production remains unchanged.

### 2026-10-12 — Read-only canonical dispatch verifier

- Audit confirmed generic non-user outcome projection lacks complete receipt
  verification. Transport/task attribution remains an activation blocker.
- Added a read-only facade over the canonical outbox evidence predicates;
  no queue/schema initialization or action API is exposed (ADR-0044).
- Verified exact signed bindings, observation cutoff, strict generation typing
  and compatibility with the existing authenticated crash-recovery fixture.
- Outcome admission/read and dependent non-user evidence integration is the
  required next step, not claimed complete by the verifier's existence.

### 2026-10-12 — Dispatch receipts connected to outcome evidence

- Generic transport/task admission now requires canonical signed receipt
  chains. Cached outcomes and dependent reflection/feedback reads recheck them.
- Positive fixtures use full authenticated chains over real test authorization
  and attempts. Unsigned new/legacy success observations are rejected or
  excluded, retaining their journal history.
- ADR-0045 records remaining duplication, clock/cutoff, projection-integrity
  and live-channel proof requirements. Production was not changed.

### 2026-10-12 — Factual replay observation-time boundary

- Sequence-only snapshots do not prove historical clock availability. Added
  optional timezone-aware observation cutoff for attempts, outcome records
  and source receipts (ADR-0046); both clock and sequence bounds apply.
- Authenticated integration tests cover exclusion, equality, ambiguous clock
  rejection and source-receipt clock skew. No operational timestamps rewritten.
- Duplicate observations, host reconciliation clock semantics and task-result
  versus user-benefit labels remain next audit work, not claimed resolved.

### 2026-10-12 — Operational completion separated from user benefit

- Audit found task success/failure directly voted on usefulness labels. Removed
  that conflation: explicit user feedback determines usefulness, while task
  completion has its own label and report counts (ADR-0047).
- Tests cover operational-only unknown usefulness, independent opposing user
  feedback, contradictory task receipts and report-level unknown calibration.
- Preference/reflection admission does not directly auto-accept task-derived
  preferences; deeper scope validation remains open. Episode label provenance,
  duplicate receipts and human/live qualification are still required.

### 2026-10-12 — Evaluator episode provenance

- Confirmed evaluator accepted arbitrary labels once attempt metadata matched.
  Scoring now reconstructs the validated privacy-bounded factual snapshot and
  rejects altered labels/evidence or silent stale-label reuse (ADR-0048).
- Replaced the scoring fixture with complete admitted authorization/attempt,
  signed dispatch and attributed feedback chains; added erasure and explicit
  historical snapshot tests. Label unit arithmetic remains a distinct test.
- Reports bind comparison to identical label/evidence snapshots, not just
  equal attempt IDs and label counts. Broader cache integrity, duplicates,
  human/live calibration and production activation remain incomplete.

### 2026-10-12 — Prediction evidence privacy and plan review

- Evaluator now enforces owner scope, clearance and expiry at generation;
  only genuinely unscoped PUBLIC context can cross user scope (ADR-0049).
- Re-read the North Star and phase gates: contract tests are not product
  qualification. Phase 0 sanitized historical corpus/longitudinal metrics,
  Phase 5 human-calibrated faculty replay and Phase 6 lifecycle/live gates
  remain explicitly incomplete.
- Run the entire local kernel regression set before collecting additional
  replay evidence; distinguish missing-runtime skips from passed checks.
- Windows full kernel set: 35 passed, one missing-runtime skip, zero failed.
  The skipped official HookRegistry/PluginManager test passed separately in
  isolated NAS/Linux Docker, as did current evaluation/outcome regressions.
  The dependency warning is retained as an unclosed Phase 6 installation item.

### 2026-10-12 — Real package admission instead of bare-loader inference

- Corrected the assumption behind the tzdata warning: bare loader invocation
  does not prepare dependencies; SKILL already requests Hermes-owned admission.
- Added opt-in disposable-profile package/lifecycle runner with imported-core
  verification and status readiness before runtime writes (ADR-0050).
- Actual current-source testing found a harmless sensitive-filename negative
  fixture blocked scanning; retained scanning and expanded synthetic non-web
  scheme coverage. Admission then failed on offline bootstrap, and a proxy
  retry failed on a core psutil Git transfer, leaving the plugin disabled.
- No successful install or lifecycle matrix is claimed. Dependency transport
  stays Hermes-owned; do not chase it by changing production environments.

### 2026-10-12 — Canonical observations across the learning loop

- Audit found per-event-ID deduplication allowed copied signed receipts to
  become extra observations. Canonical identity now uses attempt/kind/signed
  start, with original row/reference validation (ADR-0051).
- Outcome reads, reflection/preference sources and exploration exposures now
  revalidate that identity. Exposure limits apply after validation so old valid
  evidence cannot be hidden by new invalid/duplicate rows.
- Synthetic alias, legacy cache, erasure/rebuild and distinct-user-message
  regressions preserve history and demonstrate the bounded correction. Full
  projection integrity, actual effect identity and live learning stay open.

### 2026-10-12 — Canonical history survives disposable-cache loss

- Rechecked ADR-0051 and found its cache-membership election could promote a
  receipt alias after deleting the original row. Election now uses validated
  original journal observations and an indexed identity lookup (ADR-0052).
- Erased/unavailable original content remains an identity fence, not permission
  to restore copied plaintext. Malformed original references are excluded.
- Exposure reads begin at the journal and require repair for missing canonical
  rows, schema or provenance, rather than treating cache loss as empty history.
- Windows regression: 35 passed, one missing-runtime skip, zero failed; expanded
  whole-table/provenance loss cases passed separately. Seven dependent tests
  passed in network-disabled isolated NAS/Linux Docker. Production untouched.
- This closes the specific cache-deletion election hole, not arbitrary repair,
  projection integrity or large-history performance. Phase 0 corpus, Phase 5
  human/live calibration and Phase 6 actual latest-install/lifecycle/rollback
  gates remain incomplete. Do not activate based on synthetic contract tests.

### 2026-10-12 — Real dependency admission and encrypted lifecycle preservation

- Revalidated the stopped previous test and retried only in a resource-limited
  disposable container, using Git HTTP/1.1 through the existing NAS proxy.
  Public package admission completed without bypassing scanning or Hermes PM.
- Strengthened the runner to select the Hermes-owned runtime and preserve
  actual journal/checkpoint/key/encrypted-content evidence through repeated
  runtime install, package refresh, removal and reinstall. Both real runs
  passed; the stronger run closes the bounded encrypted lifecycle smoke gate.
- Added timeout evidence retention and missing/replaced-key/baseline-overwrite
  regressions. Local injected tests are distinguished from the actual run.
- Full Phase 6 remains unchecked: current release-time upstream, real GitHub
  distribution, earlier-release upgrade, native Windows/WSL, authorization
  migrations and rollback still require direct evidence. Phase 0/5 corpus,
  human calibration and live usefulness remain incomplete. Production unchanged.

### 2026-10-12 — Public baseline revision upgrade and dormant rollback

- Verified GitHub main equals the exact pre-kernel `aaf6126` baseline. Extended
  the opt-in real installer runner to install that complete tree before target
  replacement; rejected incomplete baselines before invoking installation.
- Real NAS/Linux run passed baseline-to-target replacement, legacy fixture
  preservation, dormant target-to-baseline-to-target rollback, cryptographic
  state recovery and final package/runtime removal-reinstall. No gateway ran.
- Recorded the distinction between source revision and semantic-version
  upgrades, synthetic file retention and usable credentials, and dormant
  rollback and live/crash recovery. The broader qualification gates stay open.
- Production metadata inspection found historical legacy logs but no new-kernel
  event database. It remains the legacy implementation; no claim of production
  new-kernel learning or shadow decision parity is justified. Next behavior
  work must obtain privacy-bounded history and actual shadow evidence, not
  extrapolate product usefulness from install/fault tests.

### 2026-10-12 — Privacy-bounded legacy structural baseline

- Inspected production log field shapes without printing bodies. Found text,
  previews, unsalted hashes and only a small number of delivery-audit rows;
  broad JSON copy or retrospective reward labelling would be inappropriate.
- Added a standard-library read-only exporter with typed scalar minimization,
  per-corpus identities, append/truncation accounting and bounded snapshots.
  It neither writes production state nor turns legacy logs into kernel outcomes.
- Actual final capture: 1,731 records, no malformed lines, all aware timestamps,
  no source-order timestamp regressions, four legacy sent-labelled rows and
  zero labelled outcomes. Four unknown decision groups remain opaque, not lost.
- Stored only the final structural capture privately outside the repository;
  removed two intermediate exports. Tests passed locally and the real extractor
  ran in the production image without model calls, sends or gateway mutation.
- This is partial Phase 0 evidence, not completion. Next work must expand
  historical coverage and reconstruct genuinely available shadow context;
  semantic/human labels, causal attempts and live effects cannot be guessed.

### 2026-10-12 — Longitudinal baseline and public transport correction

- Expanded the same read-only, content-free exporter to seven rotated logs
  plus the active log: 17,049 records, 2,221 distinct tick references and 35
  watcher references within this capture. All timestamps parsed; no malformed
  rows or within-source timestamp regressions. Fifteen sent-labelled rows
  remain legacy claims, not verified sends or usefulness rewards. Labels stay
  unknown. Four opaque decision groups remain unclassified.
- The private weekly corpus is outside Git with restricted local ACLs. Its
  pseudonyms cannot be joined to the earlier capture. Caller/source order is
  not causal order; repeated enforcement rows are not repeated interventions.
- Corrected ADR-0028's overly broad host-interface conclusion in ADR-0054.
  `dispatch_tool` is public, but the send helper is deliberately unregistered;
  the existing public `hermes send` CLI is a legitimate integration candidate.
  Do not install a fake registry handler to manufacture availability.
- Executed seven injected-result cases against the preserved official
  `f925b01` CLI emitter: skipped and truthy non-boolean success both exit zero;
  partial effects can exit failure. Added a digest-reporting opt-in test.
  Reviewed newer `3f2abce` source separately; no latest-runtime qualification
  is claimed. No actual platform send, production mutation or restart occurred.
- Next: loaded-registry probe and controlled CLI transport qualification, then
  genuine context/shadow replay and human usefulness calibration. Phase 0,
  Phase 5 and full Phase 6 remain incomplete; source tests do not replace them.

### 2026-10-12 — Actual public SDK and command-handler probe

- Added an opt-in fresh-process probe with a disposable home and environment
  allowlist. It calls the actual upstream PluginContext and registry rather
  than reconstructing their methods or registering a test send tool.
- Actual `f925b01` SDK dispatch reports unknown `send_message` both before
  and after importing the official send helper. The public send parser and
  list handler run successfully with an empty platform directory. This is
  fresh-manager/helper-import evidence, not full gateway discovery or delivery.
- Negative checks confirm socket creation and child process launch are
  refused before OS effects. All four exercised source digests are reported;
  no credentials, real sends, gateway startup or production mutation occurred.
- Initial local failure was missing `ruamel.yaml`, not an API failure. Added
  that dependency only to the test venv and reran successfully. Do not convert
  missing dependency diagnostics into false interface availability claims.
- Existing public CLI transport remains the next integration candidate.
  Full bootstrap, current upstream runtime, authorized-route dispatch,
  delivery acknowledgement and genuine useful behavior still need evidence.

- Repeated the actual SDK/list-handler probe and seven emitter cases against
  a separate current `3f2abce` worktree: all passed, with the same four source
  digests as `f925b01`. An initial incomplete sparse worktree caused missing
  imports; materialized the new checkout without editing upstream code or
  changing the old snapshot. This closes a bounded current-source/native
  Windows SDK check, not a complete current Hermes installation or gateway
  execution gate. No production changes or external sends occurred.

### 2026-10-12 — Full command path to a discovered local platform

- Added a test-only custom platform through public plugin discovery and
  `register_platform`; no fake send tool or patched core function is involved.
  The real command, config loader, route parser, standalone routing and result
  emitter now run together against current `3f2abce` source on native Windows.
- Six local integration cases passed: success, refusal, partial effect, cron
  duplicate skip, wrong receiver route and disabled channel. Synthetic local
  receipts prove fixture effects only; skip has exit zero but no new effect,
  while partial has exit one and an effect that must not be blindly retried.
- Solved actual test-environment failures without bypassing relay authorization:
  narrow read-only Git provenance queries, real missing dependencies, explicit
  UTF-8 capture. Recorded dependency/sandbox limitations and exact scope in
  `HOST_TRANSPORT_LOCAL_20261012.md`; production and upstream source untouched.
- Next integration work must connect the qualified public command semantics
  to authorized attempts and ambiguous receipts, then obtain actual channel
  and usefulness evidence. Full bootstrap/PM/live/canary gates stay open.

### 2026-10-12 — Process observation integration without false outcomes

- Implemented typed CLI report classification and authenticated-start-bound
  `DispatchOutbox.record_cli_observation`. Reports retain only structural
  status/exit metadata and a keyed fingerprint, never raw errors, IDs or bodies.
- Success/error/partial/skip are explicitly reported claims. None automatically
  becomes delivery, task completion, benefit or an acknowledged outbox entry.
  Unknown future fields cannot manufacture external-delivery proof.
- Actual six-case current-upstream local command results pass through the
  classifier. Synthetic authorized recovery fixtures separately prove foreign
  tokens cannot record, replay is idempotent, divergent evidence conflicts,
  raw response markers are absent and observations cannot acknowledge dispatch.
- The 36 kernel-script sweep completed with 35 passes, one missing-Hermes
  official-hook skip and zero failures. Additional classifier/recovery checks
  passed after adding divergent-evidence and claimed-proof regressions.
  This is not a production or live-usefulness pass.
- ADR-0055 preserves the gaps: qualified process launch, actual channel receipts,
  late/uncertain forensic recovery and the end-to-end live executor remain open.
  Production remains untouched and the live sender remains disconnected.

### 2026-10-12 — Text transport authority boundary

- Current public CLI media parsing can turn a text body into an attachment
  request. Added an explicit text-plan compiler rather than trusting generated
  body syntax or a one-time absence of extracted files (ADR-0056).
- Profile ownership, exact destination resolution and unchanged text parsing
  are required. Body travels through stdin; plain-mode forcing is unsupported
  by this backend and rejected, not silently reinterpreted. Media support
  remains an explicit future capability, not implicitly granted file access.
- Unit checks passed. Actual current-source host callbacks and command handler
  also passed all six local-platform scenarios with compiled plans, including
  preflight rejection of host media controls before any fixture delivery.
- No matching test process remained from the interrupted run; collected new
  terminal evidence rather than assuming its prior result. These are isolated
  fixtures, not real delivery, full bootstrap or PM-installed qualification.
- Next: bind this plan to a fresh authenticated start in a qualified executor,
  preserving uncertainty across crashes and obtaining real channel receipts.
  Semantic shadow/human usefulness and longitudinal acceptance remain open.
  Production remains unchanged; no live sender was activated.

### 2026-10-12 — Single-start execution bridge

- Connected authenticated outbox start, authorized text compilation, a final
  journal-authority recheck, one trusted launcher call and nonterminal CLI
  observation (ADR-0057). No retry/release/acknowledgement on process errors.
- Added send-time content/route/window checks and caught pending journal policy
  updates before launch admission. This is not an atomic external-effect guard;
  host identity and concurrent revocation remain integration obligations.
- Real synthetic recovery authorization passes through the bridge and rejects
  a second launcher call, changed body/route and an expired launch window.
  Failure-isolation, text-contract, recovery, dispatch migration, evidence
  projection and action-authorization checks pass.
- Launcher/parsing callbacks in the recovery fixture are synthetic. Actual
  host command tests are separate: no combined real-process/runtime qualification
  or external delivery has been proved. Next implement the operator-owned
  process launcher, then qualify the combined isolated chain before live canary.
- Production unchanged; broader semantic shadow, agenda/learning usefulness,
  deployment/migration and longitudinal acceptance requirements remain open.

### 2026-10-12 — Actual isolated process launcher

- Added immutable operator-owned process binding and pre-launch artifact/profile
  checks. No shell, body in argv, inherited caller environment or automatic retry.
  Lossless output/timeout uncertainty remains nonterminal (ADR-0058).
- Native Windows process cases pass for multiline Unicode, timeout, oversized
  output, invalid encoding and changed bindings. The real synthetic recovery
  authorization now reaches a separate synthetic child through the single-start
  bridge; repeated execution still does not launch again.
- All six actual current-upstream local-platform command cases also pass through
  this launcher, preserving stdin body and actual child-side profile/route/media
  checks. These are separate qualification paths, not yet a PM-installed host
  command combined with genuine authorization and platform delivery.
- Next address full runtime/bootstrap selection, private capture placement and
  crash cleanup, independently enforced resource limits, then combined authorized
  installed-runtime qualification before any real-channel canary. Explicitly
  retain semantic shadow/human usefulness and longitudinal acceptance gates;
  launcher tests do not substitute for a continuous attentive assistant.
- Production unchanged. No external send or production transport enablement.

### 2026-10-12 — Current source full module bootstrap

- Added an opt-in actual `hermes_cli.main` module-entry path, retaining Hermes's
  bootstrap/profile/activation behavior. Disposable profiles and selected-write
  audit checks protect the source checkout; no core function is patched.
- Six native Windows cases passed on audited `3f2abce`: success, refusal, partial,
  cron skip, wrong receiver and disabled channel. Initial cron-skip failure was
  missing fixture context; restored it and reran all cases. No core/production
  repair or dependency install was needed.
- Current upstream tree remains clean. ADR-0059 distinguishes module bootstrap
  from generated installed console entry and PM-selected installed generation;
  those broader gates remain open. Terminal results do not imply living jobs.
- Next qualify the installed runtime and data preservation, not repeated handler
  checks. Retain semantic shadow, human calibration and longitudinal usefulness
  gates: successful transport alone cannot make an attentive continuous assistant.
- Production unchanged; no external delivery or transport activation.

### 2026-10-12 — Current-source real installed-runtime job started

- Rechecked available environments: no ready managed test generation could be
  safely reused. Started one disposable NAS/Linux Docker admission/lifecycle job
  from exact Git archives (`fb11b19` Alive and audited `3f2abce` Hermes), with
  matching local/remote hashes. No production mount, credentials or gateway run.
- Confirmed the named container actually running; base dependency preparation is
  still in progress. No installation/lifecycle pass is claimed. Retained a live
  log follower so a lost foreground handle does not discard job evidence.
- `INSTALL_ADMISSION_CURRENT_3F2ABCE_20261012.md` records container, owned scratch, handles,
  evidence rules and incomplete gates. Resume the same job after revalidation;
  do not duplicate installation on an observation timeout or missing SSH handle.
- Production running with unchanged start time. Broader console-entry, semantic
  behavior, human usefulness and migration/rollout acceptance remain incomplete.

- Subsequent terminal evidence: base tooling completed, but runner argument
  parsing failed before admission due to a trailing CR from the native SSH
  script boundary. Foreground exit 1 and completed log follower were collected;
  original container is absent. Corrected line-ending transfer passed a small
  network-disabled probe. No plugin failure/pass is inferred. Preserve original
  log; next corrected attempt should use a reusable test-only tooling image.

### 2026-10-13 — Cached base and genuine core prerequisites

- Base image build completed and its actual ID is recorded. Added the test-only
  Dockerfile so tooling preparation is reproducible/reusable, not repeated per
  case. Production remains running with the same start time.
- Corrected r2 arguments were exact, but bare Python lacked core YAML dependency;
  r3 official extra preparation then refused missing required tools. Both exited
  before plugin admission. These are installed-Hermes prerequisite gaps, not
  Alive regression evidence. No hand-installed core dependencies or skipped guard.
- r4 now uses normal public core PM install with only optional browser/CUA
  opt-outs, then the existing fixture. Required tools were prepared and a real uv
  dependency process is running. Owned source/store mount preserves downloaded
  work for continuation. Exact container/log/pointer and open gates are recorded
  in `INSTALL_ADMISSION_CURRENT_3F2ABCE_20261012.md`.
- No plugin/lifecycle pass claimed yet; verify the same active job rather than
  starting duplicates. Console entry, real delivery, migration and semantic/
  longitudinal usefulness gates remain incomplete. No production change/send.

- Terminal follow-up: r4 completed core preparation but its carrier-interpreter
  fixture invocation still failed. r5 reused the exact completed environment via
  Hermes `selected_venv`/`venv_command`, then passed public plugin admission and
  the encrypted lifecycle fixture, with terminal exit zero. Repeated install,
  refresh, removal and reinstall preserved journal/checkpoint/keys/decryptable
  synthetic content. No core reinstall or manually added dependency.
- This closes the bounded audited-source NAS/Linux managed-runtime lifecycle
  check, not current published distribution, generated launcher, live migration
  or longitudinal usefulness. Evidence/limits are updated in the current
  admission record. Production remains unchanged. Next reuse the prepared
  runtime for real hook/cognition qualification and the actual console entry;
  do not return to repeated cold carrier/source-handler tests.

### 2026-10-13 — Current runtime hook and cognition evidence

- Reused the completed core environment without dependency download in a
  network-disabled container `alive-hook-20261013-r1`. Terminal exit zero,
  finished `2026-10-12T18:05:23.415119768Z`; retained `hook-r1.log` in the owned
  admission scratch. No production profile, provider or gateway was involved.
- Actual current HookRegistry/PluginManager load/dispatch contract passed,
  producing expected shadow journal records without raw fixture message/tool
  content. Separate cognition-cycle and shadow integration contracts also pass.
- Scope remains bounded: hook fixture copies a package instead of using public
  admission and overrides the documented test HOOKS_DIR seam. It reports missing
  declared PyYAML/tzdata in the core-only generation. That warning is retained,
  not hidden or solved by pip. This is loader-contract evidence, not a fully
  admitted profile/end-to-end gateway/real model/longitudinal pass.
- Next run hook/cognition checks within a publicly admitted plugin generation
  and replace the profile override seam with fresh-process profile discovery.
  Do not equate source/core-only tests with installed-user behavior. Semantic
  corpus/human usefulness, console entry and production migration gates stay open.

### 2026-10-13 — Publicly admitted installed-hook qualification

- Removed the HookRegistry path override. Fresh-process profile selection now
  precedes imports; an unavailable Hermes runtime may skip only the source-only
  fixture. Missing runtime/dependencies in installed-profile mode fail instead.
- Extended the opt-in admission runner to execute the actual installed package's
  hook test using Hermes' committed plugin-enabled interpreter. It neither copies
  another hook/plugin into that profile nor rewrites its admitted configuration.
- Immutable input Git tree `863e8198b0c018ccd0d3bddb5756b0b478e3d63b`, exact
  audited core `3f2abce7f468cf194bb7f9ff9c6a033b075d834c`. Disposable NAS/Linux
  container `alive-admitted-hooks-20261013-r1` exited zero and emitted both
  `HERMES_ALIVE_ADMITTED_HOOK_CONTRACT_OK` and
  `HERMES_ALIVE_INSTALL_ADMISSION_OK`. Hook dispatch, native tool observer,
  expected journal records and raw-content exclusion passed after public package
  admission and uninstall/reinstall. Original encrypted state still decrypted
  after hook execution; retained log/evidence is in the current admission record.
- This closes the copied-package/path-override gap for the bounded installed
  hook contract, not live gateway/model/console behavior. Shared hook-test state
  remains synthetic and disposable; no production provider, profile or sends.
  Longitudinal agenda usefulness, human semantic calibration, independent review,
  real authorization migration and production canary gates remain open.

### 2026-10-13 — Temporal trust across model waits

- Actual interleaved-event regression runs exposed two previously accepted
  failures: a deliberation response admitted after a newer exploration gate,
  and a consolidation retry disclosing retained excerpts after learning consent
  withdrawal. Both regression checks failed on the pre-fix implementation.
- ADR-0060 establishes an evidence/consent epoch across every plugin-level
  model await. Decision frame, candidate content, latest gate/selection and
  learning consent/evidence are revalidated before calls and after responses.
  Invalidated context ends that operation, not a retry using its old prompt.
- Both stages now persist an exclusive start before the first provider call.
  Cancellation/unresolved starts fence repeat use of that operation ID; no
  completion, useful outcome or action authority is invented on recovery.
- Regression cases additionally cover superseded intent, erasure, provider
  failure before retry, simultaneous same-operation callers and cancellation.
  Stable-context retries and true response-model attribution remain supported.
  These callbacks are deterministic and local; no real provider was invoked.
- This is cognition safety progress, not model-quality or complete orchestration
  qualification. Event-to-candidate/agenda orchestration, human semantic corpus,
  longitudinal usefulness and production canary are still required. Revalidation
  is not atomic with networking and cannot cancel an already in-flight request
  or govern internal Hermes provider retries. Production stays unchanged.
- Independent Windows Python 3.14 run: 36 kernel test files, 35 PASS and one
  explicit absent-Hermes-runtime hook SKIP, zero failures. This source suite
  does not supersede admitted installed-hook evidence or close live gates.
- Reused the audited core-managed runtime in network-disabled NAS/Linux
  container `alive-temporal-20261013-r1`: both updated synthesis regressions,
  cognition-cycle and recovery contracts passed, terminal exit zero. Inputs are
  immutable tree `bc5df08116dcd36cbb95258b9ef01262f076b083`; archive SHA256
  `2c720b5e9c56124d3512c23fd73255b329a61b35344f435b7ecb38cbe02a5a0b`.
  Retained owned-scratch `temporal-r1.log`, SHA256
  `03db287b47ab13609db7be8f976e3f4904b52549a02266322c9d553b8c075d67`.
  Started `2026-10-12T18:35:45.103235009Z`, finished
  `2026-10-12T18:35:49.962114724Z`. This is current source in the prepared core
  environment, not a new admitted-package/console/live-provider qualification.

### 2026-10-13 — Coordinator can deliberate, not just force silence

- The integrated coordinator previously ended every cycle in fixed safe silence;
  the model selector lived outside it. Added independent `prepare` and opt-in
  `plan_with_model` stages (ADR-0061), preserving the explicit audit-only API.
- Combined discovery ingestion, active encrypted opportunity, framing,
  exploration, model selection and ordered restart recovery in a new contract.
  Model-selected initiative and model-selected silence retain actual response
  attribution; policy-only silence spends no model call. The model callback is
  deterministic; no real provider, channel or tool is invoked by this fixture.
- Historical audit baseline inspection no longer mistakes a later model choice
  for the old silence receipt, and cannot overwrite it. Route/output failure is
  recorded as failure, not converted into a fictitious successful selection.
- This closes the coordinator/selector composition gap, not real event-to-candidate
  generation, user-policy integration, budgeted live scheduling, semantic quality,
  longitudinal usefulness or delivery. Production remains unchanged and legacy
  runtime retirement remains gated on those still-open requirements.
- Independent Windows source suite: 37 kernel test files, 36 PASS, one explicit
  absent-Hermes-runtime HookRegistry SKIP, zero failures. No live model inference
  or real user-benefit judgment is included in that result.
- Network-disabled NAS/Linux source/runtime qualification also passed in
  `alive-model-cycle-20261013-r1`: model-cycle, audit cycle, selector, recovery
  and shadow contracts, terminal exit zero. Reused audited core-managed runtime;
  no dependencies were redownloaded and no production mounts were present.
  Input tree `4bc26583d198478f74307c14a43bfcab69b33b8a`, archive SHA256
  `ae22763f3612d27829fe699b4ac09f7735f6908c22b87c8f638b24d011a86ee9`.
  Owned-scratch log `model-cycle-r1.log`, SHA256
  `e6354d4b93b4fbf316948aa7c5eb21c9ba5dbcd77d916beca0ed730cc06d7231`.
  Started `2026-10-13T05:36:22.379471833Z`, finished
  `2026-10-13T05:36:28.264430342Z`. Current-source tests in the prepared core
  environment are not a current-package/console/live-provider admission claim.

### 2026-10-13 — Source meaning can produce tentative candidates

- ADR-0062 adds owner-scoped, authenticated discovery interpretation through an
  explicitly supplied Hermes model capability. It can propose zero to four drafts
  and reasoned model judgments; it cannot grant itself authority or send.
- Evidence is revalidated after inference. Accepted drafts are encrypted; durable
  receipts preserve actual model identity and structural failures without raw
  source text or provider exception bodies. Cancellation fences repeat spending.
- Independent Windows suite: 38 kernel files, 37 PASS, one explicit missing-Hermes
  runtime hook SKIP, zero failures. These callbacks are deterministic, not live
  provider quality evidence. The live probe is separate and opt-in.
- The user authorized a bounded synthetic live experiment: at most six logical
  calls, no private conversations, no channel sends or production configuration
  changes. Existing configured primary and official fallback remain Hermes-owned.
  Actual execution/results must be recorded separately; permission is not a pass.
- Profile-memory retrieval, useful persistent commitments, real user policy and
  budgets, semantic/human review, live orchestration and production canary remain
  open. This does not complete the goal or authorize experimental deployment.
- Network-disabled NAS/Linux source contracts passed in
  `alive-opportunity-20261013-r1`, exit zero, five tests (interpretation, agenda,
  discovery, composed model cycle and recovery). Immutable input tree
  `b2b4f56774fea73c5601c5290cf9be48abb69a50`, archive SHA256
  `ae4b545284d91ac13a1aea4899deff8af5d8f99b728eb8f5a8bc14f4d045fc2c`.
  Retained `opportunity-r1.log` SHA256
  `8bba31a756fa680664c0a673b46c37b0be044560f79205a060963f4a96c0bbfd`.
  Started `2026-10-13T06:11:02.944106325Z`, finished
  `2026-10-13T06:11:08.740047759Z`. This is source qualification, not public
  installed-package or full platform qualification.
- Explicit live synthetic experiment `alive-live-opportunity-20261013-r2`
  finished exit zero at `2026-10-13T06:13:54.428237163Z` (started
  `2026-10-13T06:13:10.029821502Z`). Three logical interpretation calls used
  nine observed async HTTP attempts: six USTC attempts had no recorded HTTP
  response; three configured official DeepSeek fallbacks returned 200, with
  returned model `deepseek-flash`. This does not establish a USTC permission
  failure or production route outage; this experiment used the host proxy.
- All three cases returned zero candidates (grounded community notice with
  unknown user interest/location, unverified rumor, injected source commands).
  No candidate was rejected, no selector call occurred, no action was attempted
  and no message was sent. Silence is consistent with unknown usefulness, but
  the experiment does NOT qualify useful proactive behavior or the live selector.
  The interpreter lacks evidenced user-interest context; prioritize trusted
  profile-memory integration and paired positive/negative semantic experiments,
  rather than forcing output or embedding installation-specific interests.
- Initial live bootstrap attempt failed before inference because the test helper
  imported PyYAML, whereas current Hermes uses `hermes_yaml`. Corrected only the
  private bootstrap to write JSON (valid YAML); no dependency or production
  configuration was changed. Three of the initially allowed six logical calls
  have been used; do not silently restart a fresh six-call budget on continuation.
- Retained synthetic-only report SHA256
  `f749ccd6e3f983b91559a9edb8837bd6bddf503a4f8f0dc1ee563adde2d59ee8`
  and `live-opportunity-r2.log` SHA256
  `67412138fe71abfa92396acd0e541bec22e747de1ef5b74c1ed11dcd92cc88c0`.
  Removed the isolated credential export, temporary model configuration and its
  auto-generated configuration backup after the process terminated; original
  production credentials remain unchanged. Production gateway remained running
  with unchanged start time `2026-10-11T07:43:25.630569081Z`.

### 2026-10-13 — Explicit profile evidence reaches interpretation

- ADR-0063 connects bounded typed memory to opportunity interpretation. Owner,
  original proposal/source provenance and value digest are checked; inferred,
  forged, foreign, expired and unavailable records are not explicit user context.
- Model-wait revalidation now includes context. Withdrawal during inference
  prevents completion; context never grants action authority. Dimension evidence
  records cite supplied profile events without plaintext in the journal.
- New deterministic context contract passed, including revocation during the
  model wait. Existing opportunity synthesis contract passed with absent context.
  No additional live model calls or production changes were made this revision.
- Still required: paired live positive/negative relevance tests (three remaining
  approved logical calls), purpose/consent integration, legitimate reviewed and
  migrated profile provenance, trusted ingress, generalized retrieval, meaningful
  ongoing commitments and longitudinal human usefulness. Do not count this as
  production or semantic-quality acceptance.
- Windows regression: 39 kernel files, 38 PASS, one explicit absent-Hermes hook
  SKIP, zero failures. Subsequently corrected independent discovery/memory vault
  selection and reran both affected contracts successfully. A shared custom vault
  is now an explicit host choice, not an implicit migration or assumed layout.
- Network-disabled Linux container `alive-context-20261013-r1` passed context,
  opportunity, typed-memory and composed-model-cycle contracts, terminal exit zero.
  Input tree `fb2238f19ba2f692be577ef865e63018b12b90cc`, archive SHA256
  `60492f00811f3fd95c2e32cd35c8c78d8155e977c157915941287cadf6607e38`;
  retained `context-r1.log` SHA256
  `99cdc728fd868d58ce1d4a7a59699cddbd8f33dab99d8e685ddded916440bcbb`.
  Started `2026-10-13T06:26:00.720779041Z`, finished
  `2026-10-13T06:26:04.227637420Z`. This uses the prepared core-managed runtime,
  not installed-package or real-model qualification of this new revision.

### 2026-10-13 — Bounded live profile experiment, not acceptance

- Added explicit probe scenario selection, a 1-6 logical-call cap, synthetic
  explicit profile seeding and optional selection of the isolated profile's
  configured fallback. Candidate drafts are serializable with separate dimension
  reasons. Budget exhaustion skips selection honestly, rather than claiming a
  completed decision or invoking another model. Default CI never invokes providers.
- Offline composed-probe contract passed: three simulated calls produce a draft,
  selector choice and negative-case silence; one-call mode cannot invoke selection.
  These are fixture results, not real-model semantic evidence.
- Live paired attempt `alive-live-context-20261013-r1`, input tree
  `396ef6b5c171e18daf6bb9b823f6c345b5fa4a0a`, archive SHA256
  `2d71d1557166d735239bde7fc8f6624054ab7c00b66fed5177f03a6ae1cdf80e`,
  used two logical calls, both failed. Five observed async requests: four USTC
  ConnectErrors and one official DeepSeek RemoteProtocolError. Terminal exit zero
  only means the probe wrote its failure report, NOT successful inference.
  Started `2026-10-13T06:31:01.379287957Z`, finished
  `2026-10-13T06:31:40.780594486Z`. Report SHA256
  `e8d05caefc9a6eaee988023ac267848d024175e7be82762531d31897f0242f07`;
  `live-context-r1.log` SHA256
  `9ae7d31f0641767ce2ed49dc3f6bfb89b506ac57129585b9ce88965492f2fbb2`.
- Non-model HTTP checks confirmed the relay running and both direct/proxied
  official endpoint reachable (401 without credentials). This is not proof of
  reliable model transport or a basis to alter production routes.
- Final remaining authorized call explicitly selected the configured official
  fallback in `alive-live-context-final-20261013-r1`, input tree
  `75b7965d59cbb2c199b2f8c22a1a9aa3c86a1d97`, archive SHA256
  `9d50969b251f96292b8d62a8259da8a755aad8276b59fa053fc4906365880742`.
  One logical interpretation call, two observed HTTP attempts (RemoteProtocolError
  followed by 200), actual response model `deepseek-flash`, terminal exit zero.
  Started `2026-10-13T06:34:37.787521620Z`, finished
  `2026-10-13T06:35:07.961159916Z`. Report SHA256
  `acef41f4e1093b4eb06fe92bb05377fa64306f4752cef355c3535e5bb26fb8eb`;
  `live-context-final-r1.log` SHA256
  `7853bd7b21df69744d780d5b9cf46af1f2e771292acbbad81db577ec36d50934`.
- Produced one repair-recording candidate grounded in the synthetic explicit
  interest and online preference, retaining the source link, lack of deadline and
  uncertainty. No candidate rejected. Value 0.85, confidence 0.6 and urgency 0.1
  are model judgments, not observed outcomes. Wording remains explanatory rather
  than a qualified natural proactive voice. Live selection was deliberately NOT
  run because the budget was exhausted; no attempt or send occurred.
- Total authorized spend is now six logical calls, sixteen observed async HTTP
  attempts across experiments. No further live calls without renewed permission.
  Removed both runs' isolated credential exports, configuration and generated
  configuration backups after terminal verification. Production remained running
  with unchanged start `2026-10-11T07:43:25.630569081Z`.
- Next: durable completed-candidate recovery without re-spending, grounded intent
  through real policy/presentation/outcome stages, paired semantic review and
  longitudinal human usefulness. Do not treat one draft or transport success as
  full cognition, presentation, production or installation qualification.
- Windows suite: 40 kernel files, 39 PASS, one absent-Hermes hook SKIP, zero
  failures; subsequently reran the affected probe contract after preserving
  configured fallback endpoint/key overrides and isolating preflight setup.
- Network-disabled Linux probe contract passed in
  `alive-probe-contract-20261013-r1`, terminal exit zero. Input tree
  `8249bd3cc21662293dc0a48328ff7f23b4d98b91`, archive SHA256
  `d9332f48901e7c52ba0d30e61c84c1064ef6b04106b525f56495d1915d04e31a`,
  retained `probe-contract-r1.log` SHA256
  `446927f05222776e513763daefa4235e39b7e1b9f85d8ed6732c8bca7f43cceb`.
  Started `2026-10-13T06:39:15.274265090Z`, finished
  `2026-10-13T06:39:16.176126903Z`. Provider/network capability is mocked;
  this checks probe orchestration and accounting, not provider reliability.
- Requested renewed permission; user explicitly allowed further isolated model
  calls without a total-count limit. The unchanged scope is synthetic public
  scenarios, no private chats, no channel sends and no production configuration
  changes. Preserve the six already-used calls as historical accounting; do not
  erase them on restart. Continue with explicit small-batch budgets, causal
  receipts and transport retry accounting rather than blind repeated inference.

### 2026-10-13 — Recover the paid candidate, then deliberate

- ADR-0064 adds explicit completed-candidate recovery without inference, journal
  append, automatic permission restoration, selection or send. Recovery checks
  current source/profile scope, retained encrypted contents and causal receipts.
- Fixed original-index loss after partial rejection. New bundles preserve IDs;
  old zero-rejection bundles are unambiguous, whereas old partial bundles fail
  explicitly without deleting history or silently regenerating different intent.
- Deterministic recovery contract passed: rejected-first identity preservation,
  real attribution/counts, restart/repeat loading, default permission downgrade,
  scope/authority/incomplete refusal, bundle erasure and profile withdrawal.
- Live synthetic probe reused the existing actual candidate from the previous
  paid experiment. Zero interpretation calls, one selector call, USTC HTTP 200,
  actual response model `deepseek-flash`, choice SHARE, no action attempt or send.
  Only the test process excluded USTC from its proxy path. Production network and
  configuration were unchanged; prior isolated ConnectErrors are not evidence of
  production provider unavailability. Seven cumulative logical live calls used.
- Natural presentation and semantic fidelity, durable selection recovery, fresh
  evidence binding through later stages, outcomes, production user-policy wiring,
  live canary and human longitudinal usefulness are still open. One successful
  selection is not useful exposure, delivery, feedback or production acceptance.
- Windows suite: 41 kernel files, 40 PASS, one absent-Hermes hook SKIP, zero
  failures. Linux network-disabled recovery/opportunity/context contracts passed
  in `alive-opportunity-recovery-20261013-r1`, exit zero; started
  `2026-10-13T06:53:58.917568439Z`, finished
  `2026-10-13T06:54:01.595747478Z`. Source input tree
  `80bed4f891682b4c16cc74b3e0b290d253e265f4`, archive SHA256
  `a4a89f861a03aaeb18c6f06451a6999bb653e10cf891236b56f2607b6cf09ad6`.
  Retained `opportunity-recovery-r1.log` SHA256
  `0435b88f67228fe1f39f5c5464c4e26b49cd644b20fbf6c484b6e4b10de7976f`.
- Live test `alive-live-recovery-20261013-r1` used the same source input and the
  previous retained synthetic journal, started `2026-10-13T06:53:59.259758767Z`,
  finished `2026-10-13T06:54:20.356771956Z`, exit zero. Report SHA256
  `73a6214b7a7787bf6451faebd2d31e41d6f83fe181f0a0763b42c9a21fe8f91f`;
  `live-recovery-r1.log` SHA256
  `f07749f886a60655c62aaaac34459fab49d0c5b73e8f5c1037fbbc839a377d2d`.
  Initial extraction and later selection came from different configured provider
  routes; both correctly returned model name `deepseek-flash`. No regenerated
  interpretation or external dispatch occurred. These are source/core-runtime
  experiments, not admitted installation or complete behavior qualification.
- Removed this run's isolated credential export, configuration and generated
  configuration backup. Production continued with unchanged start time
  `2026-10-11T07:43:25.630569081Z`; no gateway restart/deployment occurred.

### 2026-10-13 — Original evidence survives no longer than its sources

- Reproduced a stale SHARE after explicit profile withdrawal during model
  selection. ADR-0065 binds generated candidate recovery through frame creation
  and selector call/return boundaries, rather than trusting retained copies.
- Eight source-epoch cases pass, including unchanged positive SHARE, rejection
  before frame copying for a foreign owner or relabeled candidate, and no retry
  after withdrawal. No action attempts or model network calls in this regression.
- Windows: 42 kernel test files, 41 PASS, one absent-Hermes hook SKIP, zero
  failures. This does not replace admitted-plugin or real gateway qualification.
- Network-disabled Linux container `alive-source-epoch-20261013-r1` ran the
  source-epoch, model-cycle, deliberation-synthesis, opportunity-synthesis and
  opportunity-recovery contracts against the selected managed Python. All pass;
  terminal exit zero, start `2026-10-13T07:19:02.780374652Z`, finish
  `2026-10-13T07:19:07.617486574Z`. Immutable source input tree
  `a2ab8c253582e9b02a293ac43be36f3ed68058dc`, archive SHA256
  `d39b44e2cad19a900dd194a255d390913c56e3ddcb195dcc7a633f2a75a195c6`.
  Retained `source-epoch-r1.log` SHA256
  `d357656bc8f581c47af8ebad9bb6bc2eae0242a5dcaaf2fe19da581e47ca087c`.
- No additional live model calls this step; cumulative logical count remains
  seven. Production running/start time unchanged. Version, release branch and
  public installation defaults were not changed. Natural presentation, further
  source lifetime binding, actual outcomes and installation/canary gates remain.

### 2026-10-13 — Connect natural expression to current style

- ADR-0066 connects current explicit presentation preferences and an optional
  host language to the renderer. No installation-specific persona or fixed
  sentence template; no learned/legacy preference silently becoming authority.
  The reviewer sees meaning/candidate only. Context is checked before/after
  both asynchronous stages; style changes and meaning withdrawal abort.
- Composition regression: typed share selection, explicit warmth, host language,
  generation and structurally independent fake review; rejects invalid language,
  changed style during generation/review and withdrawn meaning. No sends.
- Two actual USTC `deepseek-flash` generations succeeded with two observed HTTP
  200 requests. They preserve the URL and uncertainty literal. Cumulative logical
  live calls: nine; observed async HTTP requests across recorded experiments: 19.
  These two were prompt/style experiments, NOT validated selection, independently
  reviewed renders, evidence entailment, human usefulness or delivery. Reports
  explicitly mark selection/review unexecuted and delivery unqualified.
- Qualitative finding: warm/brief wording is modestly conversational; formal/brief
  wording copied the test's "synthetic public scenario" marker because we had
  wrongly placed that metadata inside a fact atom. Removed the marker from the
  fixture fact, keeping synthetic provenance outside body meaning. No renderer
  output keyword cleanup. The corrected fixture has offline validation only;
  the live evidence remains attached to its original immutable input.
- Live input tree `2cb739e5fce81215731e3ebb6cb6dbe3f9051b32`, archive SHA256
  `df612b5604c281d0883b4ae36cc753a311fb797a761341fc8947f35da9db8551`.
  `alive-live-natural-20261013-r1` terminated before inference (missing bootstrap
  module path). Verified terminal exit one/no profile, then corrected only the
  test process PYTHONPATH. `alive-live-natural-20261013-r2` exit zero; start
  `2026-10-13T07:33:36.803830264Z`, finish `2026-10-13T07:34:35.910277139Z`.
  Report SHA256 `659f45967d6ad812f024217c7a53f5159a8ea2711e9ba06a02990050b7e811f4`;
  log SHA256 `4a2ac7bbf6f53c9325af7b378e5200efc1a33130d1577ab07996d4a51b19d6d0`.
- Windows: 44 kernel files, 43 PASS, one absent-Hermes hook SKIP, zero failures;
  reran the affected probe contract after suppressing its verbose synthetic report
  on stdout (report-file assertions remain). No real network in offline tests.
- Linux `alive-natural-offline-20261013-r2`: corrected-fixture natural composition,
  paired probe accounting, semantic-review-store and presentation contracts pass;
  network disabled, exit zero, start `2026-10-13T07:36:49.754369442Z`, finish
  `2026-10-13T07:36:52.802290791Z`. Input tree
  `b0912896ccc8cbec42f25a5fc7e7b0ba7987c3cd`, archive SHA256
  `375397341cc4df3b9d9d7703f876c5250bcffda6f7c3ef8d8e271c0f4a65bbc3`;
  log SHA256 `f11a94c764078abc922fad785f4d0e05a08af8e958ac58bc956b2d3330a55a10`.
  This precedes only the probe test's stdout-suppression change.
- Cleaned isolated exported model credentials/configuration after verified live
  termination. Production still running with unchanged start time
  `2026-10-11T07:43:25.630569081Z`; no restart, send, deployment or model changes.
  Official and USTC routes serving the same model family are not independent
  semantic reviewers. Further bridge/calibration/outcome/lifecycle work is open.

### 2026-10-13 — Bind actual selected intent to proposed-content expression

- ADR-0067 adds an explicit specialized shadow review store. The original
  generated SHARE/ASK selection and frame are immutable; meaning binds that
  selection and the complete original draft as proposed content, never fact.
  This avoids an extra generative extraction changing intent. The original
  source URL is protected when present; generic semantic review must still
  assess all other claims, relations, uncertainty and unsupported additions.
- Seven composition cases passed: normal SHARE/ASK, withdrawal and erasure
  during generation, superseding selection, foreign owner, and withdrawal after
  completed review. Repeat meaning definition appends nothing. Original frame
  remains byte-identical. Review success is shadow-only; no attempted action.
- Live experiment reused the retained actual model-selected synthetic repair
  workshop draft. Zero interpretation/selection calls, one expression call,
  USTC HTTP 200, actual `deepseek-flash`. A bound encrypted model-candidate receipt
  is created and resolvable. The experiment deliberately did not invent an
  independent review or send grant. Cumulative live logical calls: ten; 20
  observed async HTTP requests across the recorded experiments.
- Qualitative read: Chinese output retains workshop content, availability,
  no-registration/deadline/purchase conditions, explicitly sourced profile
  relevance, original URL and non-verification caveat. It is still rather formal
  and explanatory, not evidence of an engaging proactive voice or benefit. No
  blind semantic qualification or human outcome exists for it.
- Windows: 45 kernel files, 44 PASS, one absent-Hermes hook SKIP, zero failures.
  Linux `alive-selected-expression-offline-20261013-r1` passes the new composition,
  semantic rendering/review store and natural presentation contracts, network
  disabled, exit zero. Start `2026-10-13T08:06:59.912055299Z`, finish
  `2026-10-13T08:07:08.844321571Z`; log SHA256
  `eca3b672db673bf0a86e89526515d0703537ade4056ff87c6ae4513c15b29fd6`.
- Both tests used immutable tree `cd9b0c54aa27132ed0059dfb6c314dc7b442f3b0`,
  archive SHA256 `61135512ef81e80edae3a63c6a7247e430cf76f5e8415f93d83d554821ae62e0`.
  `alive-live-selected-expression-20261013-r1` exit zero, start
  `2026-10-13T08:07:00.061940889Z`, finish `2026-10-13T08:07:20.378295895Z`;
  report SHA256 `9ed23219dd1f68db63e16f851abf921828fac98019b833aedd648a381746b1b9`,
  log SHA256 `5939a79b3afd6b2a5ba1bcbc4521310b91c05a43db83e5773ba01e3376937e6a`.
  The probe has a durable one-attempt fence for this selection; don't rerun it
  merely by choosing another report directory. No guessed provider independence.
- Cleaned isolated exported credential/config files after terminal confirmation.
  Production remains running with unchanged start `2026-10-11T07:43:25.630569081Z`.
  Version/public release/install defaults remain untouched. Typed decomposition
  where useful, source truth, calibrated review, reviewed-expression admission,
  outcomes/learning, current installation/lifecycle and live canary remain open.

### 2026-10-13 — Actual different-family review, not a new fallback

- User explicitly authorized isolated review with an already-configured different
  model family, synthetic/public input only, no new keys, production main/fallback
  changes or channel sends. Read only configured model names before selecting the
  private test lane. This expands experiment permission, not runtime defaults.
- First configured review lane `qwen3.6-chat` returned HTTP 403/PermissionDeniedError.
  One logical call, no review receipt or qualification. Exit zero means the probe
  wrote its report, NOT successful inference. No production model repair attempted.
- A different configured lane, `claude-haiku-4-5`, returned HTTP 200 and that actual
  response model. It reviewed the retained DeepSeek expression without generating
  or selecting again. All proposed-content meaning, speech act and literals were
  judged preserved, with no added claims. The authenticated review is resolvable
  and `shadow_eligible`, never safe for automatic delivery. Model-family attribution
  relies on configured/response metadata, not a weights audit or calibrated proof.
- Cumulative live logical calls: twelve (including the failed Qwen call); observed
  async HTTP requests: 22. One positive synthetic semantic comparison does not
  prove factual entailment, reviewer accuracy, naturalness, benefit or production
  acceptance. A shared service endpoint is not silently relabeled as an independent
  model; the actual different response model/family is checked after inference.
- Added a one-attempt-per-candidate/family probe fence. Offline contract verifies
  successful review, same-family fallback refusal, provider failure accounting,
  no renderer/selector/send, and no second call on repeat, even with another report
  directory. Main/fallback selection remains Hermes-owned; the probe's family
  argument is an explicit experiment assertion, not a public skill model default.
- Qwen input tree `17ca7349d019e5a9fa064d176b48a2fd42aa2872`, archive SHA256
  `ef475b29e60d1257b7683670db64329857e16a120b0c98929136dcca83a9d2a0`.
  `alive-live-selected-review-20261013-r1`: exit zero, start
  `2026-10-13T08:19:32.146670463Z`, finish `2026-10-13T08:19:35.346123927Z`;
  report SHA256 `c7eb4acb0274f8521408a80ff30998978c9b980ec5e2446ebcaacba8734a8252`,
  log SHA256 `0db6a8f3f91ee29b132d6bd90475ee9911f07da6ff09251ae1b46ba9846dbbe1`.
- Claude input tree `3c08a4f82f6bfdbcc9996ae91b691e608c53c530`, archive SHA256
  `6d7979e908f73486d074757ae71136d8e10791eaa68995f08a744b5563dc005a`.
  `alive-live-selected-review-20261013-r2`: exit zero, start
  `2026-10-13T08:22:24.60909Z`, finish `2026-10-13T08:22:35.552958376Z`;
  report SHA256 `216703c4de0e753dc62cc7f4d641343d45c25405a962191a35ae714b1ebf3fdd`,
  log SHA256 `4335f43c3fc49c92e1abc8d2e55005de16577629bac289309af5efc54460709d`.
- Windows: 46 kernel files, 45 PASS, one absent-Hermes hook SKIP, zero failures.
  Linux network-disabled `alive-review-contract-offline-20261013-r1` passes probe
  contract, opportunity-expression composition and semantic review store; exit
  zero, start `2026-10-13T08:26:49.181975089Z`, finish `2026-10-13T08:26:59.430279503Z`.
  Input tree `d624863f5b4f3b4b90fd477d2a4068edb3cd70be`, archive SHA256
  `e5df3acf9597a61a1364518b5d6f07e8fe5be3fd1ecfbc8b4d46c15a91349863`;
  log SHA256 `0a1ad493da1c9786074571d845e2a1b952fcd8316c043812a96ec01f6d0e35d4`.
- Removed both isolated review credential exports/configs after confirmed terminal
  states. Production running/start time remains `2026-10-11T07:43:25.630569081Z`.
  No production activation, default model changes, user exposure, outcome feedback
  or installation qualification occurred. Next: calibration and useful authorized
  outcomes, including checking that new unrelated discoveries do not unnecessarily
  invalidate otherwise current opportunities; that potential coupling is not yet
  reproduced or resolved and must not be presented as a proven defect.

### 2026-10-13 — Reviewer calibration exposes an unresolved invalid verdict

- Implemented ADR 0068: eight newly authored public synthetic examples, two
  faithful rewrites and six semantic corruptions; original runtime review prompt
  and parser, whole-proposed-content representation, no exact-literal answer
  shortcuts. Expected answers/categories are outside model prompts. This is a
  pilot, not independent human gold, factual entailment or delivery qualification.
- Actual configured `claude-haiku-4-5` reviewed all eight with eight logical calls
  and eight observed async HTTP 200 responses. Two faithful cases accepted, five
  damaged cases rejected, one invalid findings result (`SemanticReviewError`) for
  the untrusted-candidate-instruction example. Zero observed unsafe acceptances
  among valid verdicts is NOT eight error-free cases. Invalid rate is 1/8; the
  invalid case cannot be counted as correct semantic detection or injection
  resistance. No raw response was retained by the original immutable pilot, so
  the exact cause is unknown. Do not invent it from the exception class.
- Added bounded raw-response/error-stage retention for FUTURE synthetic-only
  pilot reports; never runtime/private-user journals. Offline tests cover labels
  kept out of prompts, all-accept detection (six unsafe acceptances), family
  mismatch, provider failures, contradictory atom verdict preservation as invalid,
  call accounting and duplicate-spend fences. No normalization of invalid output
  and no keyword patch to obtain a passing score. The spent fixture/family must
  not be rerun under a fresh output path.
- Cumulative real logical calls: twenty; observed asynchronous HTTP requests: 30.
  The first carrier exited before the probe/model stage due to missing carrier
  `HERMES_HOME` for PM-owned environment selection; zero model calls there.
  After checking no journal/report existed, removed only its owned empty profile
  config/directory and launched a corrected carrier using the existing managed
  environment. No production core/environment changes were required.
- Immutable live/offline input tree `aaf8627680e8b470db0f52e62030153d7281c2f7`,
  archive SHA256 `336e54e5be7944dc21a9d197d8363259e39188c6bf82505f8daf5b238537bdb1`.
  `alive-live-review-calibration-20261013-r1`: exit one before model calls,
  start `2026-10-13T08:46:41.279264557Z`, finish `2026-10-13T08:46:42.302302234Z`,
  log SHA256 `c530e68d2d89ab6d20bc71bdd150eddc9d460fe73bae127b4be25b0fdccfe48a`.
  Corrected `alive-live-review-calibration-20261013-r2`: exit zero (report written,
  not all verdicts valid), start `2026-10-13T08:48:05.123131216Z`, finish
  `2026-10-13T08:49:10.296997692Z`; log SHA256
  `598384d5a175cf0912450c943eb49d3a4a22fe2c40170d298e60b7f136f542e9`,
  report SHA256 `86d7775f8fa4d61c231ba0fc8139e5259e03a4c2dea2efdb6606a3868bb0cb29`.
  Report retained under owned scratch
  `/tmp/hermes-alive-installed-RJbQNAiD/model-only-review-calibration-20261013-r1/results/report.json`.
  Windows private copy: `../work/alive-review-calibration-report-20261013-r1.json`.
- Linux network-disabled `alive-review-calibration-offline-20261013-r1` exit zero,
  start `2026-10-13T08:46:42.222838072Z`, finish `2026-10-13T08:46:42.753704663Z`;
  log SHA256 `7f5db0aa9a21b32e1dea5e4050543bb20ac233a9f93035a934b3d90bff53e7c2`.
  This original generation predates the added invalid-response diagnostics test;
  do not claim that later coverage was exercised by this old Linux run.
- Removed the isolated model export, profile config and generated config backups
  after confirmed terminal states. Synthetic reports/journal retained. Production
  still running, unchanged start `2026-10-11T07:43:25.630569081Z`; no channel sends,
  model/config mutation, restart, release or installation qualification.
- Next: fresh non-repeated diagnostic examples if needed, general review protocol
  reliability and source entailment; scoped opportunity invalidation reproduction;
  useful authorized outcomes and longitudinal feedback. Do not let additional
  review tests replace the larger Alive objective or claim production readiness.
- Full Windows regression: 47 kernel files, 46 PASS, one absent-Hermes hook SKIP,
  zero failures. Subsequently reran the modified calibration contract locally and
  under current PM-owned Linux Python with network disabled: invalid raw findings
  retained without acceptance, and an unrelated existing journal refused before
  any call or appended fixture. No additional real-model calls in these tests.
  Updated offline input tree `0085acf7f23782015d2d0b7726a04fa58232bba6`, archive
  SHA256 `92e7343ec89acd48903a18f83b9b531e3207567928ceb4ef22cdfac3bdd47629`.
  `alive-review-calibration-offline-20261013-r2`: exit zero, start
  `2026-10-13T08:55:37.364274545Z`, finish `2026-10-13T08:55:37.911896929Z`,
  log SHA256 `7f5db0aa9a21b32e1dea5e4050543bb20ac233a9f93035a934b3d90bff53e7c2`.
  Same PASS-marker log hash as r1 does not mean identical input trees or coverage.

### 2026-10-13 — Stable discovery dependencies across a continuous cognition cycle

- Previous goal turn completed the independent-review pilot and changed test/docs
  state; the subsequent user question was a status/path report, not a code change.
  Rechecked clean HEAD `cd17ae598be73c0c2a9ffea5236b641379c8dcc8` before resuming.
- Reproduced the previously suspected window coupling with a real kernel flow:
  interpret one discovery, ingest one distinct new discovery, then prepare the
  existing candidate for model selection. Before the repair this failed with
  `DeliberationContextChanged` before a selector call. It is now a verified defect,
  not merely the earlier hypothesis. No live provider or production input needed.
- ADR 0069: revalidate the original authenticated observation dependency set in
  original order, not equality with a changing ranked discovery window. Bounded
  pinned agenda IDs are filtered together with owner, clearance, type, state and
  expiry BEFORE LIMIT; source version/provenance and decrypted content remain
  validated. Default new-discovery ranking is unchanged. Missing or invalid pins
  do not fall back to a broad query or silently substitute a fresh source.
- Both interpretation's post-await check and completed-proposal recovery use the
  pinned set. The latter supplies the existing selection/expression guards, so
  there is no separate permissive path for later model stages. All originally
  supplied discovery evidence remains required, not just the chosen item's source.
  An unselected original input being superseded still invalidates the old judgment.
- Tests now cover new arrivals before selection, during selection, during initial
  interpretation, during expression and review; twelve unrelated arrivals before
  reopening a completed partial bundle; owner/clearance boundaries and malformed,
  duplicate, empty/unhashable pins. Existing withdrawal, source erasure,
  supersession, changed intent, relabeled candidates and foreign-owner failures
  remain covered. Recovery retains exact action/content identities and requires
  fresh host authority without another model call or appended journal event.
- Network-disabled Linux run `alive-scoped-evidence-offline-20261013-r1` passed
  source-epoch, recovery, interpretation, opportunity-expression and agenda tests;
  exit zero, start `2026-10-13T09:07:15.687454295Z`, finish
  `2026-10-13T09:07:28.341879339Z`. Immutable input tree
  `52648dae41fb52f92a2fcfe04059055a0b374bcc`, archive SHA256
  `38da856754c4dbd4ed08c20fcc98af3bff83edc1c77811148cda8cb42767ed6b`,
  log SHA256 `dc6f7c8ec917ccd5e410f2abe9806bfccc71a5dcc8396832c12648f2c934ebc7`.
- No additional real model calls: cumulative logical calls remain twenty and
  observed async HTTP requests 30. Production still running with unchanged start
  `2026-10-11T07:43:25.630569081Z`; no restart, configuration/auth changes, messages,
  production deployment or public release. Experimental runtime code remains on
  the isolated feature branch, not the current production 2.9.8 installation.
- User-context freshness remains conservative; this does not prove that arbitrary
  new preferences or conflicting claims are irrelevant. Observation identity is
  not factual entailment. Next critical work: general review reliability using
  fresh diagnostic evidence, claim-to-source support and useful authorized outcome
  feedback. Do not let these dependency fixes substitute for actual ongoing
  agendas, benefit, learning or full lifecycle/production acceptance.
- Updated full Windows regression finished: 47 kernel files, 46 PASS, one
  absent-Hermes hook SKIP, zero failures. Linux evidence above exercises the same
  runtime/test code tree before this later plan entry and manifest regeneration;
  it is not a current public-GitHub installation or authenticated channel canary.

### 2026-10-13 — Evidenced feedback becomes an advisory cognition input

- Rechecked clean `ba3460175eedb82ae4287168e19d69617c3d2cfa`. Inspection found
  learning estimates had no cognition consumer: the records could not inform a
  later opportunity interpretation. The estimates API also lacked a required
  principal and could combine different subjects' evidence on the same target.
  Before connecting it to model input, added owner scoping and retained-content
  authentication, not a permissive global query fallback.
- ADR 0070: estimates now require subject, filter it before grouping/decryption,
  check original observation type/row identity/sensitivity/content ID, full
  retained-content digest and target digest, and exclude unavailable/erased
  observations from support/opposition mass. A readable representative cannot
  preserve hidden influence from another forgotten observation.
- New `CognitionLearningReader` advances outcome/reflection/learning projections
  in dependency order and reads at most eight retained owner-scoped advice entries,
  each at most 1500 serialized characters. It does not extract feedback from text,
  manufacture preferences, call models or send. Existing canonical attribution
  rejects ordinary replies and delivery outcomes as preference-signal sources.
- Opportunity interpretation now sees advice separately from explicit memory.
  Prompt instructions mark it tentative, not calibrated probability, user fact,
  explicit preference or authority. Support/opposition and signal-event provenance
  are available for relevance judgment; generated candidate dimensions carry those
  event IDs. Host authorization remains independently supplied/default NONE.
- Start receipts bind a private HMAC of the advice snapshot. Model post-await
  validation and completed-draft recovery recheck it; existing selection/expression
  guards therefore reject withdrawn/erased/expired/changed advice too. Old receipts
  lacking the field recover only with empty current advice, not retroactive hints.
- Synthetic causal composition test uses two owners with opposite feedback on
  the same target. Scoped estimates/prompt input stay separate; unknown owner and
  public clearance reveal no private advice. A tampered projected content ID is
  ignored. Erasure of one owner's observation removes its mass without changing
  the other. Advice reaches interpretation and its dimension provenance; withdrawal
  during the model call and later completed-proposal recovery fail closed.
  The prior authorization/attempt/outcome and interpreter are authored fixtures,
  not real delivery, real-model quality, actual human benefit or production learning.
- Linux network-disabled initial input tree `afcccc0cc8e6522fc217c784c01a399f0375c84a`,
  archive SHA256 `3284d85474fa3163d956306133529136741892a06e2c9006428fb51c27b4dbdd`.
  `alive-learning-context-offline-20261013-r1` exit zero, start
  `2026-10-13T09:24:55.692755897Z`, finish `2026-10-13T09:25:14.966453294Z`.
  Subsequently made the estimates API principal mandatory (instead of optional)
  and updated its callers; local affected tests reran successfully.
- Required-principal-stage Linux immutable runtime/test input tree
  `f1da339c8949014998d359415c96ff1a8c4f5c0c`, archive SHA256
  `05a969a29a7632f1a771a407644ad5ac25595b361fabe117b2fe09d4d07baf77`.
  `alive-learning-context-offline-20261013-r2`: exit zero, start
  `2026-10-13T09:29:31.579001021Z`, finish `2026-10-13T09:29:49.823618312Z`;
  learning-context, preference-learning, source-epoch, recovery and expression pass.
  Both marker-log SHA256 values are
  `54f3dc6cdc095fb8e13f018af10fb14a50695fe071498ba85653b229cf49a6a2`;
  identical markers do not assert identical input generations.
- Windows source-suite run: 48 files, 47 PASS, one absent-Hermes hook SKIP, zero
  failures. The required-principal API/caller edit occurred during that run, so
  it is not a single immutable input qualification; both affected tests were also
  run against that stage's source, with Linux snapshot qualification as above.
- No real model calls added; cumulative logical calls twenty/observed async HTTP
  30. Production still running, unchanged start `2026-10-11T07:43:25.630569081Z`.
  No production upgrade/restart, model/auth/config change, channel exposure,
  published release or lifecycle/install qualification. No credentials exported.
- Next: real-model handling of fresh synthetic feedback, reviewer protocol
  reliability and source entailment; meaningful utility/outcome feedback, current
  gateway/consent bridge and longitudinal adaptation. Complete source forgetting
  and derivative retention remain open; this test does not prove those globally.
  Natural expression still uses explicit presentation settings; learned styles
  are not silently activated. Do not equate an input bridge with production-ready
  learning or count synthetic ledger attempts as delivered actions.
- A subsequent boundary check kept custom typed-memory storage separate from
  established learning/outcome storage: configuring `context_vault` no longer
  implicitly relocates their retained content. Added a custom-memory-vault
  composition test and an explicit assertion that erased reflected advice no
  longer contributes opposition mass through a readable explicit-feedback target.
  Both affected tests reran on Windows and in immutable Linux input tree
  `a9849e326c6801cb818fb4a418fae0c5b7aac0f9`, archive SHA256
  `dee322a7cfb2abe0891b2c3c252a03589472d6deb6025e58dc4c95da0df26f3e`.
  `alive-learning-context-offline-20261013-r3`: exit zero, start
  `2026-10-13T09:35:11.819180508Z`, finish `2026-10-13T09:35:13.752499805Z`,
  log SHA256 `b4ffbd3156ac87c413ece4e7e0c2b8c94e4081366940cf2d79ffc2f4ef746cae`.
  No later runtime/test edits; later plan/manifest changes are not that input tree.

### 2026-10-13 — Actual learning input contrast identifies source-support gap

- Clean `b8829e93abddb88af6767be91c8f0caab4260819` rechecked. Added an explicit
  opt-in three-call synthetic learning probe and an offline accounting/input
  contract. Probe builds its own initially empty journal and public synthetic
  discovery/profile, not a production chat or real user's feedback. It refuses
  reuse of the same spent journal even with another output directory.
- Real `deepseek-flash` / `custom:ustc`: three logical calls, three observed async
  HTTP 200 responses. Baseline no-advice draft 408 characters; weak learned-concise
  signal draft 280; explicit detailed request with advice still present draft 607.
  All proposed one SHARE, rejected_count zero, authority NONE. No selection model
  call, authorization of generated content or external dispatch. Synthetic prior
  attempt/feedback fixtures are not delivered actions or actual human outcomes.
- Directionally consistent with advice consideration and explicit-request priority,
  NOT a causal/stochastic comparison, measured benefit, lasting adaptation or
  acceptance. Inputs/raw outputs retained in synthetic-only private report to
  support diagnosis, not hidden provider failures or repeated paid regeneration.
- ADR 0071: source support is distinct from faithful rewriting. The detailed
  draft adds an unsupported absolute zero-loss assurance from no signup/money cost.
  Later meaning fidelity could preserve that flawed original perfectly. Baseline
  exposes the synthetic source label, which may be appropriate fake-data disclosure
  here; do not infer a real production leak or blindly strip provenance/test caveats.
  Future review must distinguish input roles and permit grounded tentative reasoning
  and useful compression rather than require copying or add keyword filters.
- Cumulative logical model calls twenty-three; observed asynchronous HTTP requests
  33. Existing authorization remains synthetic/public/isolation only; no new keys,
  changed main/fallback, private conversation reads or channel sends.
- Immutable input tree `64afb657a358993edbdeca0db35e52dbc4d947c8`, archive SHA256
  `2009e9db15d6a2a98b64425edd98c9915daed31ca49631a5f358377e76f6c389`.
  `alive-live-learning-20261013-r1`: exit zero, start
  `2026-10-13T09:43:44.529478792Z`, finish `2026-10-13T09:44:53.272629159Z`;
  log SHA256 `489c0c56aeec8e28fc93ab04b174f6847f33ac6b261701b7cc21dd5e9304f1ba`,
  report SHA256 `7b2a863f05629cdf58351b39a74c45f4a09dbe00881c43f0dd25f73dcc7bd8cf`.
  Retained NAS report under owned scratch
  `/tmp/hermes-alive-installed-RJbQNAiD/model-only-live-learning-20261013-r1/results/report.json`,
  private Windows copy `../work/alive-live-learning-report-20261013-r1.json`.
- Network-disabled Linux `alive-live-learning-contract-offline-20261013-r1` exit
  zero, start `2026-10-13T09:43:44.676088069Z`, finish
  `2026-10-13T09:43:46.394444836Z`; log SHA256
  `8935175ba3cc43cdda4088d50dac707185aca1fefba680fb91f46a580b36bbc6`.
  Windows same contract passes: changed advice/explicit inputs, failed calls counted,
  bounded raw response retention, NONE authority and spent-journal refusal.
- Removed owned credential/config exports/backups after terminal confirmation;
  synthetic evidence retained. Production running/start unchanged
  `2026-10-11T07:43:25.630569081Z`. No production deploy/restart, release, activation,
  real-user exposure or installation/lifecycle acceptance occurred.
- Next critical path: independent source-support review of these retained proposals
  and fresh diagnostic semantic-review examples, then eligibility/policy/outcome
  integration. No source-support runtime or gate was implemented in this pilot;
  do not mark that gap closed merely because this architecture direction is recorded.
- Full Windows current-code regression: 49 kernel files, 48 PASS, one absent-Hermes
  hook SKIP, zero failures. Only test/probe/docs artifacts changed in this turn;
  this does not qualify a published install, real gateway cycle or production use.

### 2026-10-13 — Independent source-review pilot misses an unsupported guarantee

- Added a shadow source-support component and opt-in retained-candidate probe.
  ADR 0072 records both its boundaries and the actual calibration failure. No
  source-support delivery gate, release or production activation is claimed.
- Reviewed the existing detailed candidate, not a new generation. Actual
  `claude-haiku-4-5` / `custom:ustc`, one logical call and one observed HTTP 200.
  Verdict `supported` missed the previously identified zero-loss assurance.
  Thus structural success is NOT semantic success. Sends zero, no new generation,
  no selection call and automatic-delivery qualification false.
- Cumulative logical calls 24; observed asynchronous HTTP requests 34.
  Original live input tree `5eec99b86ee9ad332c7e40d9c540c66f32338571`, archive
  SHA256 `88ec022955d5ef7f9244589bddbd753d3d5fcc9bc98e4439499f4085d19083d6`.
  Live container `alive-source-support-live-20261013-r1`: exit zero, started
  `2026-10-13T11:43:51.476551308Z`, finished `2026-10-13T11:44:16.412710878Z`;
  log SHA256 `4df9c0aa746d5fa23504066ba7413fcabb524fda8457a2c2318514bf1ddba391`.
  Report SHA256 `3a9bab5670f57ede83fb304eeb14fccaab232380084a49dad3d39794eb8fdf05`,
  retained in owned NAS scratch `model-only-source-support-20261013-r1/results/report.json`
  and private Windows `../work/alive-source-support-report-20261013-r1.json`.
- Network-disabled Linux `alive-source-support-offline-20261013-r1`: exit zero,
  started `2026-10-13T11:43:51.615418855Z`, finished
  `2026-10-13T11:43:53.866445836Z`; log SHA256
  `3cd79c45e92ae9bef2e4583dee76e4c0c0051b64e63d5b80e5ece541ad54d723`.
  Contract checks cover scope, deletion, in-flight source change, contradictions,
  independence, one-attempt refusal and no authority, not semantic accuracy.
- Later local change retains publication times and a stable interpretation-start
  anchor in review snapshots. Earlier live/offline input is not that later code;
  no live rerun or silent retroactive verdict correction. Exact generation prompt
  clock was not retained, and start timestamp must not be described as identical.
- Confirmed both containers terminal before removing owned model-profile export,
  isolated configuration and configuration backups. Synthetic evidence/logs kept.
  Production remains running, start `2026-10-11T07:43:25.630569081Z`; no restart,
  configuration change, private chat reads, external send or wmw modification.
- Previous broad Windows run became terminal, but its output handle was lost;
  no full-suite result is inferred from process absence. Current-code focused
  tests and subsequent verifiers must be recorded separately.
- Current Windows focused source-support test passes with a losing atomic insert
  producing zero model calls. Full Windows rerun completed: 50 files, 49 PASS,
  one absent-Hermes hook SKIP, zero failures; private log
  `../work/source-support-kernel-regression-20261013-r2.log`. Runtime/test edits
  finished before this suite reached the source-support file; other tested files
  did not change during the rerun. This is not actual gateway qualification.
- Updated source-support offline Linux snapshot tree
  `b03e405320a4ec26665ef0807fd5b7fcbdad2474`, archive SHA256
  `d12a8e8bdaca064ccaa62e5dc403e19ffce8c7af329bc24ddeb86c3a487fa8c2`.
  `alive-source-support-offline-20261013-r2` network disabled, exit zero, started
  `2026-10-13T11:56:25.612221889Z`, finished `2026-10-13T11:56:27.819982539Z`;
  log SHA256 `3cd79c45e92ae9bef2e4583dee76e4c0c0051b64e63d5b80e5ece541ad54d723`.
  Snapshot includes final runtime/tests, not the later documentation/manifests;
  this focused contract is not a whole-repository manifest or install acceptance.

### 2026-10-13 — Source-support calibration and a negative method comparison

- ADR 0073 records eight predeclared diagnostic cases, then four fixed-candidate
  paired method cases (eight further calls). Expected labels/category names were
  withheld from prompts; failures, wrong-family fallbacks, invalid findings and
  label disagreements are separate, and raw bounded synthetic outputs are retained.
- All sixteen actual calls: `claude-haiku-4-5` / `custom:ustc`, sixteen observed
  async HTTP 200. Cumulative logical calls 40; observed async HTTP requests 50.
  No primary/fallback edits, new credentials, private chats, generation calls or
  external dispatch. Eight diagnostic expectations matched; both methods disagreed
  on the retained closing. No method superiority, causal learning, human gold,
  zero-error end-to-end round, production qualification or benefit is claimed.
- The exact retained candidate and source excerpt were compared with the existing
  private learning report before the comparison. Other context values were carried
  into a diagnostic envelope; it is not asserted identical to the old live snapshot.
  The positive and other-domain negative counterparts are authored, not improved
  model generations. Counterbalanced single samples are not stochastic calibration.
- Initial diagnostic immutable input tree `e3b4f6c8b0dddd3021b2d17eb26afbdf425e11dd`,
  archive SHA256 `00e630a0dc43b5e2c6ece3c36370c9f716c75d499007f673a5b35a7426d81e4c`.
  `alive-source-calibration-live-20261013-r1`: exit zero, start
  `2026-10-13T12:05:21.206371959Z`, finish `2026-10-13T12:06:40.446289724Z`;
  log SHA256 `b248378cd8bc6a2e038e6dd48da1cda7f894d3dd153f986ab50d4a874590a615`.
  Report SHA256 `976f299bd5784f60b97ebf07f581452dfdbe77d169ec923a1ac326b503892b79`.
  Network-none accounting test container same suffix: exit zero, start
  `2026-10-13T12:05:21.3380874Z`, finish `2026-10-13T12:05:22.033709294Z`,
  log SHA256 `06a00283f8884797527305d11e6c58a785d22bf7ff26df639e16c062371e56c9`.
- Comparison immutable input tree `8e7eaf2a3c66db8fd092ff72158a29eb7b98ae82`,
  archive SHA256 `f46304dd3581dd21d957fcf1336e972356e70da824cebcdeecbd01296f84a230`.
  `alive-source-calibration-live-20261013-r2`: exit zero, start
  `2026-10-13T12:11:25.606414349Z`, finish `2026-10-13T12:13:06.353000212Z`;
  log SHA256 `2bc4dffb69705a9f6aad8f3cbd1d3a7d8f4030213206e528528b11a251f88ee9`.
  Report SHA256 `a8e27fa25be1567305c3ac739481803ff09e56727de6982364e1ffa1ecf0c850`.
  Network-none support/accounting tests same suffix: exit zero, start
  `2026-10-13T12:11:25.749184673Z`, finish `2026-10-13T12:11:29.046168698Z`,
  log SHA256 `877c30347ceba083c441c08f651986c75f530c351f1ccd09ad570cd35c8da328`.
- Reports retained under owned NAS scratch `model-only-source-calibration-20261013-r1/results/`
  and `model-only-source-calibration-20261013-r2/results/`; private Windows copies
  `../work/alive-source-calibration-report-20261013-r1.json` and `-r2.json`.
  Historical `unsafe_acceptances` is author-label disagreement, not an unsafe send.
  Later code renames it without rewriting reports or labels. A longer method showed
  no superiority and was moved to tests, leaving baseline runtime behavior. These
  later changes are not the r1/r2 immutable inputs; focused final-code tests follow.
- Both jobs confirmed terminal before removing each owned model export/config and
  backup. Production remains running, start `2026-10-11T07:43:25.630569081Z`;
  no production restart, install, release, wmw change or real-user message occurred.
- Final-code focused Windows support and calibration/accounting tests pass. Also
  verified both compared prompt strings have exactly the recorded live SHA256
  after relocating the unproven method out of runtime. No broad current-code suite
  or actual gateway acceptance is inferred from these focused contracts.
- Final network-none Linux input tree `7ff7d71fd7dd67cbb02f1f4fe286022a6d4c3deb`,
  archive SHA256 `c17fda5349f9dec8d8332524079b758e8bd8cafd03b8c592a145dbc8ee6dcfb7`.
  `alive-source-calibration-offline-20261013-r3`: exit zero, start
  `2026-10-13T12:17:56.026869926Z`, finish `2026-10-13T12:17:58.618595483Z`;
  support and accounting contracts both pass, log SHA256
  `877c30347ceba083c441c08f651986c75f530c351f1ccd09ad570cd35c8da328`.
  Later documentation/manifests are not part of that runtime/test snapshot.

### 2026-10-13 — Claim-accounting diagnostic and useful expression continuity

- Added opt-in `claim_support.py`, sharing the existing source review lifecycle
  rather than duplicating retention, scope, async freshness or one-attempt logic.
  Whole-message default unchanged; claim mode does not grant send permission.
  Exact text/reference coverage is structurally checked, but semantic extraction,
  entailment and real-world truth remain explicitly unproven (ADR 0074).
- One retained-candidate logical call, one observed HTTP 200, actual
  `claude-haiku-4-5` / `custom:ustc`. Five units (two verifiable claims, one inference,
  two recommendations); aggregate supported, lexical coverage true, semantic
  coverage false. The compound ending was classified advisory/not_applicable,
  exposing primary-function versus embedded-assertion accounting, not proving
  that the original author's negative label is correct or incorrect.
- Cumulative logical calls 41; observed async HTTP requests 51. Generation calls
  zero, selection calls zero, external sends zero. No public model hardcoding,
  primary/fallback changes, private conversation read, new key or wmw action.
- Reproduced a real expression failure after twelve priority-1.0 unrelated
  observations displaced the original priority-0.5 source from the current window.
  Explicit window-exclusion assertion passes; pre-fix expression raised source
  unavailable despite valid original interpretation. Resolve pinned original
  inputs throughout expression instead of searching the newly ranked window.
- Immutable runtime/test input tree `950dc9c4824f6386e7d2c9c54802b5d0ebc1d7b3`,
  archive SHA256 `1ec36fd70e65ad5e5d0fa18d7972e85a5d306d4115e6ab7dd6200d619a19575d`.
  `alive-claim-support-live-20261013-r1`: exit zero, start
  `2026-10-13T12:31:55.954228872Z`, finish `2026-10-13T12:32:21.601828712Z`;
  log SHA256 `4df9c0aa746d5fa23504066ba7413fcabb524fda8457a2c2318514bf1ddba391`,
  report SHA256 `eb03b7c226f0a348e7e97a4542f8d386bb5778815eb510a9f97623a05b21c2ce`.
  Retained owned NAS `model-only-claim-support-20261013-r1/results/report.json`,
  private Windows `../work/alive-claim-support-report-20261013-r1.json`.
- Network-none `alive-claim-support-offline-20261013-r1`: exit zero, start
  `2026-10-13T12:31:56.138871979Z`, finish `2026-10-13T12:32:13.144268955Z`;
  log SHA256 `8ed758cd42b521c798172c12890b93c18bc95fc13f428d2c388638f23ebe9dfc`.
  Claim scope/deletion/fence/quotation/coverage contracts, whole-review contract
  and opportunity-expression regression pass. Fake role/support results are not
  independent semantic quality evidence. Later added the same ranking displacement
  during render/review waits; final-code coverage is recorded separately.
- Windows support/claim/accounting tests and original expression suite pass.
  Later final-code targeted checks at all three ranking boundaries pass. Existing
  withdrawn-profile, erased-source and superseded-intent semantics remain required;
  current intent is not frozen forever or restored after genuine invalidation.
- Terminal jobs confirmed before removing and root-verifying absence of the owned
  model export, isolated config and backups. Production running/start remains
  `2026-10-11T07:43:25.630569081Z`; no production deploy/restart/activation or send.
- Next critical path: inspect embedded material assertions independent of discourse
  function, then connect support/expression with current policy and attributed
  outcomes. Do not let further structure checks or synthetic pilots replace the
  full continuous behavior, migration, install/lifecycle and production gates.
- Final runtime/test snapshot `0e4590098d4105a657c563d56050f4eda866664c`, archive
  SHA256 `92d5dd8b96d4609eec7570bd7ed303abb3406583bc7e0f88973676ab656102f6`.
  Network-none `alive-claim-support-offline-20261013-r2`: exit zero, start
  `2026-10-13T12:39:51.034256978Z`, finish `2026-10-13T12:40:12.025230901Z`;
  log SHA256 `5ac0b0388a4b61345065c76a9a2eb6537d4c353fe0cf7c8ee79a5be5b7118a58`.
  All four focused suites pass, including all twelve expression scenarios and
  all three high-priority-window boundaries. Later docs/manifests are not that
  snapshot. No whole-repository runtime, installed gateway or production acceptance
  is inferred from these contracts.
- Before future admission, still audit unambiguous review terminal history and
  current policy at the final action boundary. Neither a support receipt nor an
  inspectable quotation ledger can supply missing user authority or repair a
  semantically disputed label. No automatic-delivery gate is enabled by this turn.

### 2026-10-13 — Unambiguous source-review recovery before admission

- ADR 0075 closes a recorded lifecycle gap in both whole-message and claim
  accounting: completed plus failed history for one operation cannot resolve as
  usable. Canonical operation/start/completion binding rejects completion aliases.
  Another operation's conflict does not globally silence valid receipts.
- Actual old-versus-new regression: loaded only the `d18f535` verifier into a
  synthetic local test process. New ambiguity assertion failed with the committed
  implementation; fixed current implementation passes. No production record was
  read/deleted or rewritten, and no provider call was made for this regression.
- Windows current whole-message and claim suites pass; tests include alias refusal,
  conflicting terminals, independent valid receipt preservation, source deletion,
  owner isolation, method changes and spent-operation refusal. Such lifecycle
  correctness is necessary but not semantic accuracy, source truth or user benefit.
- Immutable runtime/test input tree `daa1ed982a8caba24d7f44013ce9a95a1475bfea`,
  archive SHA256 `4958c7cc698e5e87e0c4709b745cf0f12f9a206bb167a5f4fe5f77f4a4a60947`.
  Network-none `alive-review-terminal-offline-20261013-r1`: exit zero, start
  `2026-10-13T13:01:21.638092211Z`, finish `2026-10-13T13:01:25.516456646Z`;
  log SHA256 `4f8e5d4967ada98fe3b27ed0c0bef2067b12ed04ca25bf7ccc3ea88d3ed01da9`.
  Source/claim/accounting focused suites pass. Later docs/manifests are not that
  snapshot; no broad installed-runtime, gateway or lifecycle acceptance is inferred.
- No new real model calls: cumulative logical calls remain 41, async HTTP requests
  51. No temporary credential export was created; no model, channel, private-chat,
  wmw or production configuration mutation. Production running/start unchanged
  `2026-10-11T07:43:25.630569081Z`.
- Next critical path remains mixed-unit material-assertion accounting and the full
  current-policy/admission/dispatch/attributed-outcome chain. Do not count a recovered
  review as permission, manufacture a new operation to hide interrupted history,
  or replace the actual continuous behavior and production gates with more guards.

### 2026-10-13 — Original input lifetime at the action boundary

- ADR 0076 records an actual synthetic execution failure: forgetting a generation
  profile input after selection still allowed send-time authorization. Original
  event existence and retained candidate copies were insufficient.
- Shared selected-source recovery now runs at authorization, before consuming an
  execution start, and immediately before trusted launch. Checks remain outside
  writer transactions, validate scope before frame resolution, and preserve the
  original pinned input window. Separate context vaults are supported explicitly.
- Twelve local synthetic opportunity execution cases pass, including clean and
  unrelated-ranking positive controls, forgetting/erasure at three boundaries,
  and separate-profile-vault recovery. Authorization, CLI execution bridge,
  dispatch evidence projection and dispatch migration regressions also pass.
  These fixtures use explicit test-host authority and exact later confirmation,
  not automatic permission or a qualified external transport.
- No real model calls or sends. Read-only NAS inspection confirms production
  running with unchanged start `2026-10-11T07:43:25.630569081Z`. No production,
  other-plugin, wmw, model, authorization, channel or proxy configuration changes.
- Still required: reviewed expression must become the exact executable contract;
  semantic mixed-unit assessment, trusted launch and independently observed
  outcomes remain incomplete. A pre-launch read is not atomic with delivery.
  Continue the full long-term agenda/memory/adaptation, migration/rollback and
  production acceptance scope; do not count structural regressions as real sends.

### 2026-10-13 — Exact confirmed expression enters the execution chain

- ADR 0077 connects retained natural expression to a destination-free executable
  contract without modifying the original selected frame. Authorization binds
  both expression and derivative content identities; attempt/outbox projection
  resolves that exact contract, and start/pre-launch recheck the original expression.
- This is limited to original USER_CONFIRMED authority and later exact owner
  confirmation of both selection and expression. Review results do not grant
  automatic delivery. The required autonomous delegation/quality path remains
  open; do not substitute repeated user approvals for the long-term product goal.
- Cached authorization recovery now revalidates original input freshness and
  expression binding. Operation reuse cannot switch expression identity. Historical
  records remain intact when the recovered view is denied.
- Synthetic tests cover changed exact wording through attempt/outbox/start/launch
  checks, preserved original draft, missing exact confirmation, original expression
  erasure despite a retained executable copy, and withdrawal before permit replay.
  These are local structural fixtures, not external delivery or ten-call acceptance.
- No provider calls, private chats, external sends or production configuration
  changes. Source-support/semantic qualification and pragmatic mixed assertions
  remain unresolved. Next continue the user-delegated quality/admission path and
  trusted host/outcome attribution, plus derived-copy forgetting and the full
  persistent agenda/memory/adaptation, portability and rollback requirements.

### 2026-10-13 — User delegation without corrupting discovery provenance

- ADR 0078 separates user permission to communicate from discovery agenda origin.
  Explicit signed grants bind owner/current policy/exact route/SHARE or ASK/
  maximum sensitivity/expiry, without upgrading original generated authority.
  Grant recovery and dispatch route checks reject revocation and scope changes.
- Twenty-four local execution modes pass, including eight new delegated scenarios
  without a per-message confirmation parameter. The dedicated scope/authenticity
  suite and authorization/outcome/dispatch-evidence regressions also pass.
- Immutable tree `737f02c2b0ce6771bd4fa486a42f84f79fb9f4c9` passed four focused
  suites in network-none `alive-delegation-offline-20261013-r1`, exited zero.
  ADR records archive, times and log digest. This is isolated Python/runtime evidence,
  not a qualified Hermes gateway, complete lifecycle matrix or actual delivery.
- No provider calls or sends. Read-only production inspection confirms running,
  unchanged start `2026-10-11T07:43:25.630569081Z`. No production grant/configuration,
  other plugin or wmw modification. Cumulative actual model calls remain 41.
- Next implement trustworthy user-command/onboarding integration and autonomous
  quality admission with bounded cadence; do not turn permission into source truth
  or a topic-keyword gate. Natural expression still requires exact confirmation
  until its automatic quality path is qualified. Continue actual host delivery,
  attributed outcomes and longitudinal benefit rather than accumulating only
  structural guards; all memory/agenda/adaptation/portability/rollback obligations
  remain part of the final goal.

### 2026-10-13 — Atomic cadence and concurrent input recovery

- ADR 0079 separates consumed delegated starts from diversity exploration,
  delivery success and user benefit. Grants carry customizable generic cadence;
  the owner-wide rolling-day/interval check shares the start append transaction.
  New grants/routes do not reset history; another owner is isolated.
- Actual committed-component regression reproduces two starts for one declared
  slot. Fixed concurrent one-slot exclusion and two-start positive control pass
  through pre-launch validation. Writer-lock timestamping avoids invocation-time
  inversion caused by transaction waits. Uncertain starts still consume capacity.
- Parallel recovery uncovered false-stall and backwards-acknowledgement races.
  Deterministic old context-reader failure plus an actual reflection checkpoint
  traceback identify the causes. Idempotent projecting readers now coalesce later
  acknowledgements; strict manual checkpoints and genuine stalls still reject.
- Twenty-six local execution modes and focused cadence/journal/outcome/dispatch
  tests pass. Seven suites also pass in network-none managed Python 3.13 against
  immutable tree `48df6a35c0cf607bdb4adbb3c8f1bbf7f6a0b0cc`; ADR records archive,
  container terminal times and log digest. No actual send/user-benefit claim.
- Production remains running, unchanged start `2026-10-11T07:43:25.630569081Z`.
  No real model call, private chat, production grant/configuration, other-plugin or
  wmw change. Actual model call total remains 41, observed async HTTP requests 51.
- Continue automatic quality admission and authenticated onboarding/feedback,
  qualified delivery/outcomes and longitudinal benefit; do not mistake frequency
  safety for useful cognition or reduce the full memory/agenda/adaptation,
  forgetting/migration/rollback/portable lifecycle and production acceptance scope.

### 2026-10-13 — Orthogonal discourse/assertion diagnostic; live result unavailable

- ADR 0080 addresses the representation issue behind the mixed recommendation
  observed in ADR 0074: main discourse function no longer exempts separately
  recorded material assertions. Exact segments and anchored assertion facets reuse
  existing evidence/epistemic validation. No default method or automatic gate changes.
- Synthetic tests pass for unsupported assertions across all discourse functions,
  malformed/orphan references and encrypted recovery. A deliberately omitted-claim
  case remains semantically unproved. Lexical completeness is not extraction accuracy.
  Existing claim/source suites and three network-none NAS focused suites pass.
- Two bounded live experiments against the retained public synthetic draft, on
  already configured Haiku then Sonnet review lanes, both end with ReadTimeout/
  outer TimeoutError and no findings. No empirical semantic improvement is claimed.
  Exactly two started/two failed/zero completed review records are retained. No
  regeneration or send occurred. ADR records immutable inputs, reports and times.
- Cumulative logical calls now 43; observed async HTTP attempts 55, including
  timeout and no-terminal-status attempts. Exact temporary credential/config exports were removed
  only after confirmed terminal processes and verified absent as root. Production
  running/start unchanged `2026-10-11T07:43:25.630569081Z`; no production model,
  channel, authorization, other-plugin or wmw changes.
- Do not tune per-message patches or count service failures as algorithm success.
  Continue semantic qualification when a configured route is available, alongside
  authenticated feedback/onboarding, actual delivery/attributed outcomes and the
  full long-term memory/agenda/adaptation, forgetting/migration/rollback and portable
  production acceptance requirements. The overall goal remains active.

### 2026-10-13 — Personal-owner feedback attribution, ADR 0081

- Actual reproduction accepted a foreign actor's correctly linked typed feedback
  as the personal owner's outcome. Matching source/outcome actors alone was too
  weak. Admission and immutable recovery now require the personal owner principal.
- Foreign human/model outcomes and legacy cache injection no longer enter current
  outcomes. A migrated foreign feedback row cannot train preferences; positive
  owner feedback still contributes its bounded weight. Original journal retained.
- Local outcome, preference learning, reflection and evaluation suites pass.
  Ordinary reply and delivery success do not imply useful benefit. This does not
  establish authenticated real ingress or semantic correctness of feedback.
- Production is read-only verified running, start still
  `2026-10-11T07:43:25.630569081Z`. No model call or send; cumulative logical model
  calls remain 43 and observed async HTTP requests 55. No other-plugin/wmw changes.
- Continue actual content-linked authenticated feedback, longitudinal utility,
  natural expression qualification and the full memory/agenda/adaptation,
  forgetting/migration/rollback/portable lifecycle and production acceptance scope.

### 2026-10-13 — Owner-controlled learning recovery, ADR 0082

- Baseline `188ab23` actually accepted another person's reflection approval and
  preference withdrawal. Shared personal-owner causal validation now rejects both,
  including model principals, without blocking genuine owner controls.
- Current reflection and preference advice recover owner control from canonical
  events rather than restored accepted/active cache flags. Pending valid withdrawals
  already suppress advice; later projection acknowledgement does not grant authority.
- Derived reflection signals cannot outlive their original basis. Five local suites
  pass, including cognitive prompt/recovery invalidation of a withdrawn observation.
- No actual model call/send, production restart/configuration, private chat, other
  plugin or wmw change. Production still running with start
  `2026-10-11T07:43:25.630569081Z`; logical model calls remain 43, async HTTP attempts 55.
- Continue semantic/authenticated content-linked feedback and utility validation,
  expression qualification and the original full long-term memory/agenda/adaptation,
  forgetting/migration/rollback/portable lifecycle and production acceptance scope.

### 2026-10-13 — Semantic feedback stage, no preference authority, ADR 0083

- Previous feedback tests began with manually interpreted targets. New opt-in
  FeedbackSynthesizer interprets an original complete consented owner reply against
  its preceding delivery and exact signed executed text. Hermes still owns routing.
- Several topic/presentation/timing/interruption hypotheses can remain separate,
  with original quotes, situational/durable/uncertain scope and unresolved meanings.
  It writes no preference weights, approved reflection, profile fact, job or message.
- Synthetic tests cover consent/delivery/time/truncation bounds, model-wait withdrawal,
  erased evidence recovery, private receipt storage and spent IDs. A wrong meaning
  with a valid quote deliberately remains structurally admissible: actual semantic
  quality is unproved, and automatic learning authority is always false.
- No real model call/send, private chat, production configuration/restart, other
  plugin or wmw change. Logical calls remain 43, async HTTP attempts 55.
- Next: genuine public-scenario model/independent-review qualification and bounded
  tentative learning integration, not per-example keyword patches. Real ingress,
  complete input capture and derived-copy forgetting remain open alongside the full
  long-term cognition, memory, migration, lifecycle and production acceptance scope.

### 2026-10-14 — Real semantic evidence and per-unit error isolation, ADR 0084

- First three prospective synthetic interpretations complete on configured main
  deepseek-flash; configured Qwen3.5 review considers them acceptable with explicit
  limits. Shared frontend/reported names and agreement are not semantic ground truth.
- Three new cases expose one irony validation failure, not a transport failure.
  A separately recorded diagnostic repeat captures the original output: three
  reply-grounded hypotheses plus one hypothesis quoting the sender, previously
  rejected as an entire interpretation. No irony-specific rule or source repair.
- Per-unit quarantine now preserves valid hypotheses and explicit rejected indexes.
  Partial receipts/recovery expose counts; the probe does not call partial output
  structurally complete. No automatic learning or profile/job/send authority.
- Observation regression preserves rejected public synthetic output while excluding
  potentially secret provider exception text. Actual failed histories stay failed.
- All four live containers are confirmed terminal and exact credentials removed.
  Production running/start unchanged `2026-10-11T07:43:25.630569081Z`; no private
  chat, send, other-plugin, production configuration or wmw change. Actual logical
  calls now 51; observed async HTTP attempts 63, counting failures and repeats.
- Six distinct corpus cases attempted, four untested; not ten zero-error full Alive
  calls. Continue semantic/utility qualification, appropriate incomplete-result
  handling, authenticated host integration, expression, long-term memory/agenda/
  adaptation, forgetting/migration/rollback/portable lifecycle and production scope.

### 2026-10-14 — Remaining prospective feedback cases expose protocol omissions

- All ten distinct prewritten public synthetic cases now attempted. Eight first
  attempts structurally complete; irony originally fails and explicit topic
  boundaries produce a partial result. This is not ten zero-error complete calls.
- The topic-boundary model output understood the meaning but omitted per-signal
  uncertainty fields. No fabricated defaults or example-specific prompt patch.
  Fixed diagnostics separate malformed protocol from unsupported reply quotes.
- Four additional actual calls / four HTTP 200; cumulative 55 logical / 67 observed
  async HTTP attempts. Six containers terminal, all exact model exports absent;
  production start unchanged, no actual sends or preference/configuration changes.
- Next: bounded model-driven contract recovery and independent assessment of
  partial results, followed by tentative learning utility qualification and the
  unchanged full host, expression, memory, agenda, portability and production scope.

### 2026-10-14 — One-shot model-driven feedback recovery, ADR 0085

- New opt-in recovery consumes canonical partial receipts, only reconsidering
  rejected indexes. Accepted parent units remain untouched. Explicit abstention
  and unsupported replacements remain visible; no semantic defaults are invented.
- One journaled recovery per parent, including failure/cancellation, with consent,
  source integrity, expiry and attribution rechecked after model wait and on use.
  Fake regressions cover concurrent/repeated attempts, invalid target indexes,
  erasure/withdrawal during wait, source erasure recovery and provider-secret exclusion.
- Initial probe setup exposed diagnostic-wording versus receipt-identity confusion;
  fixed by original raw digest binding. First actual model recovery exposed a redundant
  mandatory outer reason. Removed this duplicated requirement for non-null signals,
  retaining all evidence/signal fields and explicit explanations for abstention.
- An explicit fresh-copy repeat structurally recovers three units on one main-model
  call. Original partial and failed-recovery histories remain unchanged. Eight isolated
  offline suites pass; not semantic proof, independent review or ten clean full calls.
- Actual model totals 57 logical / 69 observed async HTTP attempts; all temporary
  recovery model exports absent, production unchanged and no real channel send.
- Next: independent semantic assessment and bounded tentative learning utility,
  including incomplete-output integration. Continue the full long-term memory,
  agenda/adaptation, authenticated host, expression, forgetting/migration/rollback,
  portable lifecycle and production acceptance scope. Recovery is not yet runtime-wired.

### 2026-10-14 — Preserve evidence meaning across learned context, ADR 0086

- Different-family Qwen3.5 review considers recovered boundary, deferral and question
  interpretations acceptable but flags permission/enthusiasm and timing ambiguity.
  No confirmed per-example error is patched; review agreement is not ground truth.
- Found that weighted estimates/context discarded encrypted rationale. Canonical
  validated rationale/source/origin/direction notes now reach opportunity cognition;
  masses and authority are unchanged, original qualifications are not truncated.
- Synthetic regressions distinguish three same-polarity meanings and assert notes
  in the model input, plus existing owner/clearance/erasure/withdrawal defenses.
- Actual call totals 58 logical / 70 observed HTTP attempts; review terminal and
  credentials absent, production start unchanged. No new preference, real send,
  private read, model setting or wmw change. No production preference changes;
  synthetic tests still create authored fixture observations. Full acceptance remains open.
- Next measure counterfactual operational benefit, integrate bounded tentative
  feedback only after utility qualification, and continue full host/expression,
  long-term memory/agenda/adaptation, forgetting/migration/rollback and portability.

### 2026-10-14 — Matched advice ablation, no demonstrated benefit, ADR 0087

- Three prospective synthetic pairs clone canonical evidence and remove only
  notes from one arm. Same prompt/mass label, alternating order; sequential clock
  and one-sample stochastic variation remain limitations, not hidden controls.
- Six actual calls/HTTP 200. Two pairs choose no draft in both arms; the meeting
  pair proposes similar shares in both. Its apparent acceptance difference is
  validation: a 143-character explanation exceeds the old adapter's 128 cap.
- Align rationale capacity with the domain's existing 512-character bound without
  truncation or authority relaxation. Tests cover 129/512 acceptance, 513 rejection.
  Report model-empty versus parser-rejected drafts separately. Original result stays.
- Totals 64 actual logical calls / 76 observed async HTTP attempts; live container
  terminal, credential exports absent, production unchanged. No actual send,
  private read, learned update or production/wmw/other-plugin configuration change.
- Next: discriminating fresh cases with matched explicit baseline interests and
  positive/negative controls, repeated decision/utility assessment, then bounded
  feedback learning and the unchanged full production objective. Do not equate
  more accepted drafts, silence or a passing parser with user benefit.

### 2026-10-14 — Discriminating controls expose missing abstention semantics, ADR 0088

- Three fresh blinded pairs add matched explicit interests/availability and a
  relevant source plus an excluded commercial source. All six arms retain useful
  drafts; this is not evidence that rationale notes improve decisions.
- Two model outputs encode skipping as an empty communication draft and are
  correctly rejected by the existing contract. Another asks to reconfirm an
  already explicit boundary. Preserve these partial/weak results, not a zero-error claim.
- Next separate source-linked non-action decisions from executable drafts, with
  reasons and material-uncertainty requirements for questions. Do not implement
  advertisement keyword rules, manufacture preferences or treat silence as approval.
- Totals 70 actual logical / 82 observed HTTP attempts. Live container terminal,
  exact credential exports reverified absent, production running/start unchanged.
  No actual sends, private reads, production/wmw/other-plugin changes.
- Continue fresh semantic and downstream utility qualification before genuine
  feedback learning integration; retain the full host, expression, long-term
  memory/agenda/adaptation, forgetting/migration/rollback, portability and
  production acceptance objective.

### 2026-10-14 — Separate source non-action from cycle silence, ADR 0089

- Opportunity results now retain encrypted, source-linked reasons for abstention,
  independent of executable drafts. Missing decisions remain unassessed; malformed,
  foreign, duplicate or contradictory skips are counted separately, not invented.
- Recovery rechecks source/context/learning freshness and encrypted bundle integrity.
  No skip becomes user dislike, learned evidence, dispatch or action permission.
- Seven isolated Linux suites pass, with Windows synthesis/recovery/abstention and
  paired-probe checks. Actual replication: five of six calls structurally complete
  with useful drafts and reasoned skips; the first emits invalid JSON and stays failed.
  No reconfirmation questions in valid results; no blind semantic or utility proof.
- Totals 76 actual logical / 88 observed HTTP attempts. Credentials removed and
  verified absent after terminal state; production running/start unchanged.
- Next qualify fresh decision contexts and source support, consider bounded
  model-driven contract recovery without retroactive success, then genuine tentative
  feedback integration. Full host, expression, layered/external memory, sustained
  agenda/adaptation, forgetting/migration/rollback, portable lifecycle and production
  acceptance remain required; no deployment or real send in this exploration.

### 2026-10-14 — Fresh contexts, blind diagnostic and canonical link binding, ADR 0090

- New opaque paired contexts cover narrow interest, unknown eligibility and
  untrusted source instructions. Six structural completions preserve useful
  drafts and skips; utility/source entailment and note superiority remain unproven.
- A different-family blind diagnostic misses engineering concerns and emits a
  code-fenced response rejected by strict parsing. Keep that failure, not a green gate.
- Found a source-link hole: expression only protected URLs already in drafts.
  Canonical provenance now forms a separate LINK atom when omitted, without
  mutating the selected frame/draft or inferring authority. Long URLs retain exact
  discovery bounds, and renderer omissions fail before semantic review.
- Totals 83 actual logical / 95 observed HTTP attempts. Both inference containers
  terminal, credentials removed and verified absent; production unchanged.
- Next validate fresh source/decision semantics and all selected delivery paths,
  then useful attributed outcomes and bounded feedback learning. Retain the full
  memory/agenda/adaptation, authenticated host, forgetting/migration/rollback,
  portability and production acceptance scope; no production deploy or real send.

### 2026-10-14 — Provenance before selection/confirmation, ADR 0091

- New source-aware original contracts bind exact provenance before user approval,
  while encrypted model wording and explicit presentation-policy versions preserve
  audit/recovery. No post-confirmation append or rewriting of historical contracts.
- Broader long-source tests expose generic candidate and model-atom capacity
  mismatches. Typed validated channel envelopes use bounded channel capacity;
  generic/frame/prompt caps remain. Expression reads original accepted wording
  and a separate canonical LINK atom, rather than treating formatting as model speech.
- Component and authorization/outbox fixtures prove exact contract/frame continuity,
  not genuine host authorization/delivery. Six cached synthetic replays require
  explicit new-key source-ID remapping; one gains a link and none infer permission.
  Original failed exact-ID replay stays recorded, not migration/recovery proof.
- Actual model counts remain 83 logical / 95 observed HTTP attempts. No new model
  export, private read, actual send or production/wmw/other-plugin change.
- Next qualify source/decision semantics and natural expression, then useful
  attributed outcomes and bounded feedback. Continue the full host, layered/external
  memory, sustained agenda/adaptation, physical forgetting, migration/rollback,
  portable lifecycle and production acceptance objective.

### 2026-10-14 — Actual composed shadow chain and strict JSON transport, ADR 0092

- Eight actual calls across two fresh public synthetic contexts cover interpretation,
  selection, expression and configured cross-family fidelity review. One chain's
  review is shadow-eligible, never delivery-safe; the other fails fenced JSON parsing.
- Found the critical distinction: generated practical additions can survive fidelity
  review without being sourced. Next evaluate selected draft/source support separately,
  allowing explicitly tentative useful reasoning without pretending it is sourced fact.
- Four adjacent stages share finite/unique/bounded JSON decoding with exact outer
  fence normalization, not bracket repair, schema defaults or model-failure rendering.
  Explicit nesting limits replace reliance on machine recursion settings.
- Totals 91 actual logical / 103 observed HTTP attempts; live container terminal,
  all five temporary model/profile exports removed and verified absent. Production
  start unchanged; no private read, actual send, learning or configuration change.
- Continue useful end-to-end attribution/learning plus the full host, layered/external
  memory, sustained agenda/adaptation, physical forgetting, migration/rollback,
  portable lifecycle and production acceptance scope. No production deployment.
