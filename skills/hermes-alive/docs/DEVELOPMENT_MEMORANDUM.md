# Hermes Alive — Development Memorandum

Internal engineering notes. User-facing README files describe the product;
failure history and non-regression constraints live here.

## Control wiring is not complete execution qualification

2026-10-24 (Asia/Shanghai), Codex; ADR0213. Only actual admitted Core commands in
the confirmed owner conversation may enable/pause/query. Store full-envelope
signed activation tied to finite existing grants. Config hints cannot mint or
renew authority. Startup must not revive legacy/shadow when new setup is paused.
Model/fallback management stays in the shared Core slot; public-query consent
does not imply private profile/chat access or automatic learning. Keep pending
and reap capabilities on any discovery preparation wrapper. Reuse current
continuity on repeated confirmation/startup instead of closing an active bridge.
CLI disable must revoke the real policy, not legacy files only. Report durable
authority separately from live task state and channel delivery. A no-model
start/stop fixture is control evidence only; interrupted active-cycle recovery,
actual ordinary cycles, migration and consumer/fleet/quality gates remain open.

Pre-cognition cooldown and final cadence reservation must share the same verified
owner history, including uncertain starts and grants from before renewal. The
advisory read is not a reservation; final writer-transaction checks still win.
Skip source/model work during a cooldown and recheck in the standard cycle, not
only after expensive cognition. Cross-process policy OFF must reach paused without
unnecessary route/tool/model work. Use the exact embedded package for dependencies;
the observer loader's module allowlist is not a general import/activation API.
Keep `kernel-shadow` non-sending even with retained grants. Native activation
requires the explicit `kernel` lifecycle engine, not just execute=True or a
renamed UI label. Native-engine discovery/startup consults signed state even when
the disposable Core setup hint is missing; an absent fresh store is unconfigured,
while a damaged existing inventory requires recovery, never key replacement.

## Standard submission must use Core parsing and owning continuity

2026-10-24 (Asia/Shanghai), Codex. Prior standard executor fixtures supplied
synthetic target/media callbacks; they did not qualify Core's actual parser
boundary. CoreSessionRouter.standard_send_parameters uses resolve_send_target
and BasePlatformAdapter.extract_media, the current home accessor and canonical
owning adapter/thread resolver. Its continuity bridge must belong to that same
router and clearance. Assembly has no IO or route/delegation authority. Keep
parser callback identity assertions, legal native target/thread resolution,
missing/wrong-clearance refusal and no-send-before-execution checks. Do not repair
Core or weaken its parser to accept an unrealistic synthetic chat identifier.
Actual transport remains synthetic in this fixture, not delivery/product proof.

## Continuous is an explicit lifetime, not a grant or retry policy

2026-10-24 (Asia/Shanghai), Codex; ADR0212. Reuse the durable/native host loop.
Continuous execution requires execute=True, continuous=True, no finite budget and
a positive interval. Bounded shadow semantics remain unchanged. Pause or failure
ends the loop; each new cycle binds a fresh native caller and current authority.
Authorization/reconciliation/content attention and unavailable consumed attempts
also stop; unknown dispositions fail closed rather than silently continue spending.
Do not restart an uncertain cycle, promote shadow state, infer remote delivery,
change public cadence defaults to satisfy a test, or add a second physical FIFO.
Component lifetime and synthetic standard-send fixtures are not ordinary installed
activation or consumer lifecycle qualification.

## Started once does not mean running now

2026-10-24 (Asia/Shanghai), Codex. GatewayHostBinding.startup previously
returned already_started after its bounded host task had terminated. Observe the
owned task on repeated startup inspection instead: distinguish running, stopping,
budget/stopped, cycle failure, exception, cancellation and unknown completion.
Do not restart a completed or failed generation implicitly. Keep unresolved
native work visible independently of loop liveness, and do not expose exception
messages, private task results or infer external delivery. Unload is not proof
that native work or Core-owned transport has drained. Regression tests must hold
the live task open explicitly rather than depend on scheduler timing.
This component observation is not ordinary activation or daemon qualification.

## Guided configuration is not activation, migration or implied retention

2026-10-24 (Asia/Shanghai), Codex; ADR0211. Operator setup and the selected
authorized conversation are different trust boundaries. The Core CLI issues a
short-lived confirmation; an actual Core command source and exact existing
SessionStore scope confirm it. Do not derive the target from model text, the
latest chat, an invented user/subject ID, environment fallback or a fabricated
session. If the slash command is the first interaction and Core has no session,
ask for an ordinary message, do not create a routing entry to make lookup pass.
No source without Core admission is authorization just because its fields match.

Confirm outbound history separately from model/delivery. Show retention duration,
model inheritance, public-query scope, disabled inbound/automatic learning and
configuration retention before presenting the code. Pending choices are sealed,
expire, and their unowned duplicate is erased after confirmation. Never log the
code or raw user/session/source data. Do not read credentials to configure Alive;
model routing/auth/fallback remain Core-owned. Existing state is preserved, not
silently relabeled as another realm's principal.

Recovery must not manufacture authority. Replay cannot override a later OFF or
rewrap erased content. Fence a missing retention write at its original confirmed
sequence under the writer lock; project newer consent ahead of earlier replay.
Status/startup/confirmation require the existing journal and BOTH keys. Explicit
initial setup may initialize an empty store, but never replace missing migration
keys or accept a truncated identity key. Such an inventory fault needs recovery,
not a new installation identity. Preserve synthetic missing-key tests and legacy
content/key/grant preservation evidence; neither proves actual legacy migration.

Return configured_not_activated until the real execution assembly exists.
Do not silently invoke the legacy watcher or claim enabled=True from metadata.
CLI denial tests must inspect the structured reason, not just exit2 (which could
also be an unrelated parser/import error). Public discovery, actual CLI/command
dispatch and runtime reinstall are component evidence, not a remote consumer,
paired real account, daemon restart or full live lifecycle qualification.

## Verify the real main turn; keep bookkeeping out of conversation

2026-10-24 (Asia/Shanghai), Codex. A direct Core context collector pass does not
show that an actual AIAgent turn preserves its scope/context through request
assembly. The opt-in probe must use actual run_conversation and observe actual
request messages, with no supplied share/history/system overlay and no enabled
tools. Compare decoded sidecar content: raw JSON substring tests mis-handle the
exact share's escaped newlines. Save original responses for semantic review, not
just a green wrapper. Scope/grounding and conversational utility are separate.

Keep machine IDs/status/schema separate from what the user should hear. An
unknown collector reading scope is explicitly unknown, not an empty reading
range or proof of full-page/video consumption. Relevant limits should be
explained in ordinary language; do not show the source-record inventory as the
answer. This is a general boundary of the context contract, not replacement
rules for a particular answer, topic or word.

Model fallback belongs to Core. A completed turn through the official fallback
does not qualify the configured primary. A pre_api_request event is not proof
that a physical HTTP attempt occurred (cooldowns/pools can intervene). Record
fallback activation and current route without altering production configuration.
Core get_version_info returns VersionInfo; use its display_version/commit/source,
not guessed package metadata or a dictionary API. The failed first setup remains
failed, not a model call or passing probe. Model-only credentials and full traces
stay in private isolated storage, never Work or the repository; teardown checks
the real container state before removing the projection. Reports must refuse
credential disclosure, and the operator audits private artifacts before cleanup.

## Exact prepared content is not a delivered conversation turn

2026-10-24 (Asia/Shanghai), Codex. The continuity store must capture before IO,
not after a normal return that could be lost in a crash. Its event is explicitly
share_prepared, not sent. Only authenticated existing adapter observations add a
success/error/unknown report; none is remote delivery, user viewing, a canonical
quote inventory or an instruction to retry. Main-agent context must preserve
these limits, exact content and reading scope. Never fabricate a transcript/user
turn or let source text issue instructions. Core admission/scope precedes content
decryption; retention consent does not grant sending or replace pairing.

Do not use expiring planning/candidate resolvers for historical conversation.
Separately consented outward history has its own original deadline; replay must
not renew it. Source expiry (including physical sweeping) is not user forgetting:
keep the exact outward text with unavailable grounding, but never restore expired
source excerpts. Explicit source/subject erasure must suppress dependent context;
a durable authorized forget request blocks reads even before its erase worker
finishes. Retention OFF stops new capture, not previous consented history. Drain
the retention projection instead of trusting its first1000 records. Test source
expiry both before and after sweeping, original-owner isolation before decrypt,
reset, failed/unknown submission, cold store and actual Core hook composition.
The current explicit attachment and synthetic adapter are component evidence,
not ordinary activation, a natural main-agent answer or consumer qualification.

## Exact Core conversation scope is not a bare user ID or an authority grant

2026-10-24 (Asia/Shanghai), Codex. gateway_session_bridge must use Core's actual
persisted routing entry, restored receiving-bot identity and metadata. Resolve
the exact admitted turn/key, not a recent session; compare runtime home, user,
platform, workspace/thread, receiver and current conversation ID. A new/reset
conversation cannot inherit an old scope just because its chat key is unchanged.
Do not mutate the routing entry while restoring a snapshot or create/touch a
session to make a lookup succeed. A disconnected receiver cannot borrow the
runtime's other connected bot; read-only follow-up context is not an instruction
to submit another message. Scoped principal v2 is separate from historical
raw-user-ID ownership: no automatic memory/grant reassignment or data deletion.
Route knowledge alone grants neither pairing/authorization, content retrieval
nor sending. The ordinary host must still perform current Core admission and
Alive permission/retention checks before reading content or launching IO.

Keep test operation IDs separate from dependency-generation identities. A broad
launcher rename changed an unrelated PM generation path, failing before Python
ran. Preserve the failed launcher/exit; do not repair the good environment or
call that a product failure. New bind mounts must fail on a missing source rather
than implicitly create an empty directory. Snapshot and dependency inputs remain
immutable across qualification operations.

## Registration must not materialize deferred platform configuration

2026-10-23 (Asia/Shanghai), Codex; supplement to ADR0209. Manually instantiated
contexts passed while real public discovery timed out. Actual thread stacks
showed Alive's register() calling load_gateway_config(), which tried to load a
deferred platform under the discovery lock held by the waiting parent thread.
Never read fully materialized Gateway config or import SDKs during registration.
Use Core's enum plus its non-materializing registered_names inventory, refresh
after discovery through the Core listener, and unsubscribe on unload. Inventory
membership is not connection, destination authorization or permission to send.
Regression must use actual public discovery with configured deferred platforms,
not only a synthetic already-loaded manifest or a private loader outside its
lifecycle. Preserve timed-out inputs/stacks; do not raise deadlines or prewarm
platforms to hide the defect. No Core lock/loader modifications are authorized.

## A share journal is not main-conversation continuity

2026-10-23 (Asia/Shanghai), Codex; ADR0210. The owner reported that legacy Alive's
separate model output cannot be naturally discussed with Hermes afterward. The
new kernel's internal share/source history does not by itself fix that defect:
the standard adapter sender currently has no main-conversation grounding bridge.
Treat this as an explicit final product gate, not an already solved memory feature.
Verify actual unquoted and quoted main-agent follow-up, durable recovery, honest
submission states and session isolation. Never make the test pass with a synthetic
user turn, a hand-injected test-only prompt, a second transport queue or a claim
that a stored record means the recipient or main agent has received its context.

## Dependency compatibility is a supported API range, not yesterday's host patch

For current Core, use its version_info/manifest admission API, not the legacy
hermes_cli.__version__ placeholder. A read-only actual-source experiment proved
clean0.22.5 Git provenance and the old <0.22 declaration's real rejection without
any install stamp. The candidate now declares >=0.22.5,<0.23; unsupported older
hosts should get a clear admission refusal, not a silent legacy execution path.
Version acceptance alone does not prove dependency resolution or installation.

2026-10-23 (Asia/Shanghai), Codex. The earlier crypto50.0.0 equality avoided forcing
a newer patch onto the then-supported Core. Current stable supply instead locks
50.0.1. Keeping the equality now conflicts with the host instead of protecting it.
Declare the compatible50.x API range, retain50.0.0 as the minimum and the exact CI
fixture pin, and let Core PM honor its own exact lock. Do not force50.0.2, downgrade
the host, mutate its environment with raw pip/uv or relock Core to get a green test.
Fresh PM environment and plugin admission remain separate actual checks.

Preserve diagnostic failures: the first fresh-build layout put PM tools on a
noexec Docker temporary mount; the second forced the image's3.13 bootstrap Python
against a3.14-only current lock. Neither justifies a Core patch. Keep /tmp noexec,
give the isolated profile a normal executable owned volume and let PM choose its
own pinned toolchain. Do not call a reused or repaired partial build a fresh one.

## Sending permission must not require invented delivery proof

2026-10-23 (Asia/Shanghai), Codex; ADR0208 supersedes the execution eligibility
restriction of ADR0028 only for newly and explicitly authorized v2 channel routes.
Do not turn an unavailable remote-delivery receipt into an inability to use normal
Hermes channels, nor label request acceptance as delivery to bypass that restriction.
The host reports its truthful capability. A new owner grant chooses the required
evidence level and exact host snapshot; legacy grants retain their strict meaning.
Old failures, grants, starts and outcomes must never be silently reinterpreted.

The standard execution branch must consume the same single-start outbox and exact
reviewed body. Resolve the actual receiving bot/profile/thread/workspace through
the host, never choose a default adapter or reconstruct a second routing policy.
Keep routing metadata, interim-stream protection and actual renderer provenance;
never tag the body from a configured current model or host-supplied model hint.
Normal adapter returns are bounded sanitized observations, not CLI reports,
complete bubble inventories, remote delivery, human attention or training labels.
Long sends can return after a local lease expires: preserve the same-generation
observation without reviving the start. Cancellation/errors/observation failures
must not resend. No new FIFO, chunk interception, deterministic body or judge.

## Narrow correction must not restyle unrelated useful expression

2026-10-23 (Asia/Shanghai), Codex; see ADR0206 and the living plan for qualification.
A legitimate factual review can coexist with owner-liked explanation. Re-authoring
the whole message to fix one attribution regressed the unaffected introduction and
format. Re-running a fresh reviewer with a localization schema then missed the
same valid finding. Do not turn repeated judging into a search for a green verdict.

New corrective authoring consumes the existing authenticated negative review and
original source/candidate binding. The model proposes exact unique affected spans
and replacements or abstains; the host computes offsets, preserves everything else
and retains encrypted reconstruction evidence. This proves edit boundaries, NOT
semantic minimality, source truth, reader satisfaction or permission. The resulting
whole message still needs the same fidelity and final source review. Unknown/broad
or unsafe corrections fail visibly, never a deterministic digest or full rewrite.
No topic keyword patch, banned phrase, length quota, new memory/queue or extra judge.

New method frozen before provider calls; old starts and failures keep old semantics.
Recovery must resolve the original review, owner/source context, original candidate
and edit proof with current retention/erasure checks. Missing proof cannot inherit
the ancestor's approval or silently repeat inference. A previously confirmed body
cannot be auto-edited under its old confirmation. An unsent positive sample rating
belongs only to that exact sample, not all facts, revisions or permanent interests.

Keep launch scripts immutable while their process is active. Updating the runner
for a later operation can corrupt the earlier shell's remaining input even when
its inner test process finishes normally. Record inner test evidence and outer
terminal status separately; a printed PASS cannot override a failed wrapper or a
missing exit status. Preserve the failed attempt, qualify a separate exact candidate,
and do not rerun an old inference or overwrite history to manufacture success.

## Optional acquisition must not destroy initial understanding

ADR0205 follows an actual whole-cycle abort caused by a PDF textual URL's final
period. Do not repair model-copied URLs or silently strip punctuation. The host
owns exact citation spans and IDs; the model chooses references. Reject optional
choices locally and retain explicit invalid versus abstained outcomes. Existing
initial evidence remains usable, but failed extra reads remain unknown. Consent,
owner/source withdrawal, provider failure and physical uncertainty are not
optional-content errors. Preserve historical v1 starts and results without new
inference or retroactive acceptance. This improves acquisition, not automatically
the usefulness or naturalness of the eventual unsolicited message.

## Real distribution closure, not a private repaired installation

Reviewed 2026-10-23 (Asia/Shanghai), Codex. Follow
[RELEASE_ACCEPTANCE.md](RELEASE_ACCEPTANCE.md) and the deployment's current shared
multi-platform/governance contracts. Consumer install/upgrade must use a remote
committed artifact and Hermes' managed dependency flow without hand-editing the
installed tree. Native Windows needs actual Windows Hermes execution without
Bash; WSL2 needs real thin environment smoke, not another full Linux regression.
Keep component, lifecycle, semantic quality, physical delivery and production
evidence separate. Record terminal status durably before a tool session expires.
One accepted owner sample or an automatic model review cannot close the ten-round
quality gate. Shared status is coordination evidence, not a production lock or
reusable authorization; historical handoffs are superseded, not rewritten.

## Withdrawal must invalidate derived receipts

A once-valid semantic review cannot survive the owner's withdrawal of its
meaning. Checking only during creation is insufficient: every meaning,
render and review read must recheck current withdrawal, including after a
restart. Authenticate the withdrawal, verify owner identity before decrypting,
and make retries idempotent. Do not promise deletion of delivered messages or
recall of in-flight provider requests. Keep forget/erasure as a separate control.

In async receipt tests, start a new clock phase after asynchronous execution;
fixed offsets from process start can falsely put later selections in the
future on slower filesystems. Never weaken production causal validation to
make those tests pass.

## Correction is succession, not in-place repair

Never change the old encrypted meaning in place or carry its selection/review
authority into a corrected version. Keep the full prepared successor encrypted,
withdraw the original durably, then define that exact successor. Faults before
and after the withdrawal boundary need separate tests. Preparation identity
must not depend on retry-time timestamps, or a crash before withdrawal can
strand an otherwise identical request. An old retry must not resurrect a later
withdrawn successor. Preserve expiry, subject, sensitivity and unchanged atom
evidence. Treat the replacement as the user's assertion, not observed truth.

## Content discovery is not delivery evidence

A meaning definition does not mean a message was sent. History must say what
it records and never infer delivery from content or selection. Filter the
owner in SQL before decrypting; use event-anchored pagination instead of an
offset that shifts under concurrent inserts. Withdrawn, expired and erased
records cannot carry cached previews. An interrupted successor definition is
pending, not a successful correction. Cursors are read-only seek anchors, not
semantic validity or action authority.

## Later same-user traffic is not causal feedback

An inbound message after an action is not necessarily a reply to that action.
Require exact host-resolved attempt attribution. An ordinary linked reply is
not explicit feedback/correction/dismissal unless the host records that user
operation. Model-authored outcome details cannot manufacture user intent.
Admission fixes do not retroactively sanitize cached outcomes or learned
projections: audit and revalidate those before activating the new kernel.

## A historical green projection is not current evidence

New admission checks do not sanitize rows admitted by older code. Revalidate
their journal bindings on read and preserve invalid history rather than
deleting it. Cover direct SQL consumers as well as public projection readers;
reflection/preference caches can otherwise bypass the improved outcome API.

Reuse journal attribution checks without constructing projections under an
existing write transaction; schema initialization can deadlock on a second
connection. Revalidate accepted/active caches as well as new admissions.
Signal weights must match the journal, and reflected influence ends when the
source reflection expires, even if the signal itself remains unexpired.

## Receipt checks must not construct an executor

Reusing canonical dispatch predicates is preferable to another receipt schema.
Expose only read-only verification for learning consumers, with no queue setup
or action methods. Bind policy to original authorization and reject booleans
as lease generations. A verifier existing is not proof that outcome admission
or cached/dependent reads actually call it; test those integrations separately.

Unsigned positive receipts hide integration defects. Use signed start/result
chains over validated attempts in positive fixtures and keep unsigned receipts
as negative/legacy-cache cases. Bind cached outcome kinds to the journal so
transport acknowledgements cannot masquerade as explicit user feedback.

## Model synthesis must never become Dream again

The semantic need is real, but the old coupling is forbidden. Conversation
interpretation must not combine raw transcript persistence, plugin-owned model
routing and direct memory mutation.

Permanent constraints:

- retention permission and model-learning permission are separate;
- Hermes owns model credentials, primary/fallback routing and channel state;
- only the actual response model is valid attribution;
- evidence text is untrusted prompt data and every citation must refer to the
  bounded evidence window;
- parsing is candidate-local: one malformed candidate does not erase valid
  siblings, and no malformed candidate is repaired with phrase-specific rules;
- model output can create only expiring review proposals, never active memory,
  commitments, actions or user authority;
- raw prompts, raw responses and provider error bodies are not durable data;
- repeated operation IDs cannot repeat the model call;
- no timer or startup hook may invoke synthesis until replay evaluation proves
  usefulness, false-memory rate and review burden are acceptable.

Regression proof lives in
`tests/run_alive_kernel_consolidation_synthesis.py`; the architectural contract
is ADR-0018.

Schema validity is not semantic quality. Consolidation evaluation must use the
complete blinded-review contract in ADR-0019. In particular, do not report
precision without missed durable claims, do not report recall from a hand-entered
aggregate, do not merge sensitive and ordinary unsupported errors, and do not
hide how many review decisions the user would have to make. The synthetic seed
only tests the evaluator; it is never release evidence.

## Event existence is not subject authority

Any kernel projection that cites another event or durable object must prove the
reference belongs to the same subject (or is deliberately subject-neutral).
Never treat a syntactically valid event ID, `USER_EXPLICIT` enum value or real
agenda item as sufficient authorization. Agenda proposals, agenda transitions,
deliberation evidence and deliberation agenda references all require explicit
subject/actor checks. Cross-subject negative tests are mandatory before a new
component joins the cognition cycle.

## Integration must not smuggle in execution authority

The first cognition coordinator ends in deterministic safe silence by design.
Do not add a provider call, sender, tool executor or “temporary fallback” to it.
Future model selection must consume the durable frame through its own reviewed
boundary; future action attempts must recheck current policy and context and
produce their own receipts. A green integrated-cycle test proves persistence
and replay, not permission to act.

The model-selection boundary now exists under ADR-0021. Keep it non-executing:
it may persist a validated intent but must never create an action attempt,
deliver content or run a tool. Rejected candidates must be removed before the
prompt, not merely described as forbidden to the model. Actual response model
identity is mandatory and raw provider failure bodies are never receipts.

Do not collapse selection and execution. ADR-0022 requires a fresh, short-lived
authorization receipt. Direct observation is not user delegation; generic
inbound activity is not confirmation. No sender may treat an expired receipt
as valid, and idempotent lookup must never revive it. Keep `system_critical`
and migrated delegation fail-closed until typed authority provenance exists;
critical gateway notices remain a Hermes-core responsibility.

Never restore a direct `selection -> action.attempted` path. ADR-0023 requires
consumption of an exact live authorization receipt and rechecks latest state.
Recovery order is causal: agenda, frames, exploration, selections, outcomes.
Changing that order can silently turn valid online history into rejected replay.
Do not accept an authorization receipt by field shape alone; verify its local
HMAC and preserve `kernel/identity.key` during managed migration.

Dispatch is an ADR-0024 outbox, not a direct function call. Preserve the
authorization deadline, lease generation and transport idempotency key. Never
persist raw lease tokens or worker IDs. During reconstruction, authenticated
terminal evidence wins over a missing outbox row: restore acknowledged and
reconcile the outcome; never resend.

Never authorize from a `PolicyContext` supplied by a caller. ADR-0025 makes
the latest authenticated, user-owned autonomy policy the authority source.
Authorization and dispatch must bind its exact event and revision. A pause or
policy replacement revokes queued work, and resume must require fresh intent;
do not resurrect an old row. Historical policy replay must not directly mutate
the outbox because older events would revoke future work during reconstruction.

Do not equate a lease with an external attempt. ADR-0026 makes
`dispatch.started` the conservative point of no assumed return. Before start,
a lease may expire or be released. After start, missing evidence is
`uncertain` and must never be auto-requeued. Any terminal adapter event must
bind the start-event ID and lease generation. When migrating v2 state, map old
leases to uncertainty; preserving liveness is not worth risking duplicate
external action.

Do not let model-authored content smuggle transport authority. ADR-0027 makes
action documents strict and destination-free, binds their keyed authenticator to
the permit, and revalidates them at every later boundary. A platform, profile,
recipient, chat, thread, adapter or tool name belongs to a separately
user-authorized Hermes capability binding. `PluginContext.inject_message()`
acceptance is not evidence that an external message was delivered, and private
gateway runner fields are not a distribution-safe substitute for a public
host contract.

ADR-0028 makes that host contract executable policy rather than documentation.
Always distinguish `request_accepted`, `turn_completed`, and
`external_delivered`. Only the last may authorize `hermes.channel.send` across
the Alive outbox. The route must come from an exact user-authorized binding,
remain encrypted at rest, and be bound to the latest authenticated host
snapshot. A new host snapshot deliberately stales old routes; migration must
ask the user to confirm or deterministically re-authorize them, never silently
carry them forward. Route revocation after authorization must revoke pending or
leased work, while a durable prior `dispatch.started` remains uncertain and is
never retried automatically.

The official stable Hermes `v0.21.6` contract at commit `f27cdbce` exposes
`PluginContext.inject_message()`, but its own docstring says success means only
that a host accepted scheduling. `BasePlatformAdapter.send()` and terminal
delivery bookkeeping exist inside the gateway but are not a public plugin
capability. Until that changes, keep the new live bridge disconnected. Do not
resurrect `_gateway_runner_ref`, private adapter maps, or SHA-gated core patches
to bypass this boundary.

Do not restore full-history scans to dispatch acquisition and do not replace
them with a fixed look-back window. ADR-0029's evidence index is disposable,
not authoritative: advance facts and checkpoint atomically, run every call to
its captured watermark even when that takes multiple batches, and re-read and
authenticate journal events before changing dispatch state. Batch size may
bound lock duration but must never bound correctness. Recovery and corruption
repair may erase this projection and replay it from sequence zero.

## Discovery observations are not permission to speak

Legacy Discovery mixed collection, ranking, preference mutation, deduplication
and delivery. Never reproduce that coupling in the kernel. A collector may
create encrypted evidence and an expiring opportunity only. Its score is a
hint, not user value, urgency, route or execution authority. Source failure is
health evidence and must not become an opportunity. Exact rediscovery is
idempotent; a material update gets a new version and supersedes the prior
opportunity.

The legacy bridge is dual opt-in, bounded, external-source-only and one-way.
Its output must never feed the legacy watcher, reserve a topic, call a model or
send. Raw titles, summaries, URLs, source labels, authors and chat IDs must not
enter the journal or rebuildable projection. Local filesystem discovery needs
its own explicit consent/privacy design and is not silently included under the
external-source migration. Regression proof is
`tests/run_alive_kernel_discovery_opportunities.py`; the architectural contract
is ADR-0030.

## User availability and character rhythm are different ontologies

Session leases, queue integrity and recent interaction are user-context facts.
Alive's sleep phase, sleep debt, “drowsiness” and “forced awake” state are an
optional character/presentation model. Never place them in the same authority
chain. An assistant being awake does not mean the user welcomes interruption;
an assistant being asleep does not prove the user is unavailable.

Direct activity may block, but lack of activity must remain unknown. Explicit
availability is still not action authority, and a newer active-session fact
must override it for timing. Missing, corrupt or unauthenticated availability
state fails to unknown. Hard exemptions, user autonomy policy and send permits
remain later independent boundaries. The legacy Circadian live gate is a
migration debt, not the target design. Regression proof lives in
`tests/run_alive_kernel_availability.py`; the architectural contract is
ADR-0031.

## Presentation may shape form, never facts or initiative

Do not reconstruct the legacy `VoiceEngine` inside the kernel. Message length,
vocabulary, emojis, ordinary replies, silence and time of day are ambiguous
signals. They may support an expiring advisory estimate, but must not silently
become active style, relationship state or permission to speak.

Only a same-subject explicit instruction may enter the active presentation
plan. Accepted reflection or explicit feedback remains advisory until a later
reviewed promotion design exists. Never store `social_urge`, ignored-message
punishment or guessed `relationship_stage` in presentation state. A resolved
plan must not select content, alter claims/amounts/dates/uncertainty, choose a
route or authorize an action. Corrupt state returns neutral defaults. Before a
live renderer consumes this policy, require semantic-fidelity tests and user
inspection/correction controls. Regression proof lives in
`tests/run_alive_kernel_presentation.py`; the architectural contract is
ADR-0032.

## Disposition comes after intent, never before it

Do not replace old mood arithmetic with a newer weighted “aliveness” or
personality score. `energy`, `boredom`, `annoyance`, `affection`, ignored counts,
relationship stage and `social_urge` are not evidence that an action should
exist. In particular, silence is not an emotional injury.

An explainable disposition may annotate only an already validated selection.
Every cue must map to one independently audited decision dimension and retain
its evidence IDs. It cannot admit a candidate, change a selection, grant a
permit, pick a route or rewrite facts. Silence and non-communication actions
have no expression stance. Consumers re-authenticate and recompute rather than
trusting stored labels. Regression proof lives in
`tests/run_alive_kernel_disposition.py`; the architectural contract is
ADR-0033.

## A schema is not semantic proof

Never treat valid JSON, protected-token coverage, embedding similarity or a
renderer's self-review as proof that a rewrite preserved meaning. Style-transfer
evaluation has separate style, preservation and naturalness axes, and no one
automatic metric closes the production gate.

Define meaning before presentation as bounded encrypted semantic atoms. Lock
dates, amounts, links, contacts, negation and uncertainty exactly. A candidate
references that meaning; a renderer cannot invent its own destination or
authority. Deterministic verbatim layout may prove only transformation
fidelity. Free model output stays `review_required`. Missing a protected
literal is a hard failure; absence of the complete original sentence is not,
by itself, proof of failure because a valid paraphrase may change every
ordinary token.

An independent review must bind the exact candidate digest and inspect every
atom, additions, speech act and protected literal. The renderer and reviewer
must use distinct executions and declared independence domains; changing a
display name is not independence. A clean result is eligible only for shadow
comparison and can never authorize delivery. Keep omission, contradiction,
unsupported addition, polarity, uncertainty, time, quantity, reference and
speech-act errors as separate metrics. The checked-in multilingual seed is a
test of the evaluator, not evidence that any model pair is production-ready.

Keep four proof obligations visibly separate: factual entailment, rendering
fidelity, action authority and route authority. A green result in one must
never stand in for another. Revalidate the exact latest selection whenever a
render receipt is consumed. Regression proof lives in
`tests/run_alive_kernel_semantic_rendering.py`; the architectural contract is
ADR-0034. Independent-review and complete-cohort regression proof lives in
`tests/run_alive_kernel_semantic_review.py`; its boundary is ADR-0035.

Never persist a bare semantic `pass`. Store candidate text only in the
erasable vault and bind the journal receipt to its digest, renderer execution,
validated selection and meaning. On every read, re-run the dependency chain;
an authentic historical receipt is not current authority after expiry,
superseding selection or content erasure. Review prose does not belong in the
journal. Regression proof lives in
`tests/run_alive_kernel_semantic_review_store.py`; see ADR-0036.

The shadow comparator (ADR-0037) records its start before calling a provider.
Never retry an unresolved operation under the same ID or turn a failed review
into success. Hermes owns fallback; independently verify response model and
route metadata afterward. Model-family independence comes from a host resolver,
never from a model's statement or a task alias. Async intent changes and
content erasure must invalidate returned output. Injected tests prove execution
contracts only; real-provider and human-calibrated quality remain open.

The first real reviewer replay (2026-10-12) demonstrated why annotation scope
must be recorded. A seed that lists one focal risk per candidate cannot support
issue precision: additional overlapping classifications need human judgment.
Do not rewrite gold labels to match model output or treat the seed as a
qualification corpus. Preserve failed routes in the cohort, withhold aggregate
metrics when any case is unscored, and rescore saved results without spending
another model call. Evidence is in `SEMANTIC_REPLAY_20261012.md`.

## Plugin dependencies must respect the Hermes environment lock

The supported Hermes runtime already provides `cryptography==50.0.0`. Alive's
content vault needs AES-GCM, not a newer patch release. Declaring
`cryptography>=50.0.2` caused an isolated plugin install to upgrade the shared
environment against Hermes' exact lock and an MSAL upper bound. Tests still ran,
but the environment was no longer dependency-consistent.

Permanent constraints:

- dependency success means a consistent Hermes environment, not merely an
  importable module after an installer prints a conflict warning;
- pin cryptography to the supported Hermes lock while this plugin targets the
  current Hermes compatibility range;
- change the pin only together with a newer Hermes compatibility declaration
  and a clean-image dependency-resolution test;
- never use an unrelated system Python as evidence for the Hermes plugin
  environment.

## Location onboarding is optional, bounded, and multi-provider

Location/weather personalization must never be an installation prerequisite.
It may improve proactive context only after explicit user confirmation.

Required resolution order for user-entered city/district text:

1. Open-Meteo Geocoding (`geocoding-api.open-meteo.com`), no API key;
2. Nominatim (`nominatim.openstreetmap.org`) as an independent fallback;
3. unresolved user text with weather disabled when both fail.

An explicit `latitude, longitude` pair is an offline escape hatch and must not
perform network I/O. The guided flow must never require coordinates from a
normal user.

The IP-based coarse suggestion may attempt Nominatim reverse geocoding, but a
reverse-lookup failure returns the already available coarse city candidate. It
must not abort or stall the rest of installation.

## 2026-10-02 incident: OpenStreetMap DNS failure

One supported WSL environment could resolve and reach
`geocoding-api.open-meteo.com` but received DNS `SERVFAIL`/interfered answers for
the entire `openstreetmap.org` zone. The old forward geocoder depended solely
on Nominatim, so a normal city correction could fail and the assistant treated
the onboarding flow as blocked.

Root defect: Nominatim was a single point of failure, and isolated provider
availability was confused with overall plugin readiness. Proxy diagnosis does
not solve that product defect.

Permanent constraints:

- do not make a single public geocoder mandatory;
- contain DNS, TLS, timeout, HTTP, JSON, empty-result, and schema failures per
  provider;
- never synthesize coordinates from unresolved text;
- complete onboarding safely with weather disabled when resolution fails;
- preserve the user's text so the location can be corrected later;
- test primary success, fallback success, total network failure, and offline
  coordinate input independently;
- do not add provider API keys or inherit a developer's proxy settings.

## Release proof

`run_location_weather_onboarding.py` must prove:

- Open-Meteo succeeds without touching Nominatim;
- Nominatim succeeds when Open-Meteo fails;
- both providers failing leaves onboarding complete and weather disabled;
- coordinate input performs no network request;
- no public IP or raw lookup payload is persisted;
- existing confirmation, lifecycle, managed-config, and weather-composer
  contracts remain green.

## Query language is not the machine locale

Open-Meteo's `language` parameter selects a localized place-name search index,
not merely the response language. A Chinese place name such as `合肥` returns
no result from the English index even while the provider is healthy. Falling
through from that empty result to an unreachable Nominatim endpoint recreates
the apparent onboarding hang.

The input script therefore takes precedence over a container's often-generic
`C.UTF-8` locale for CJK, Cyrillic, and Arabic place names. A regression test
must prove that Chinese text sent under `C.UTF-8` uses Open-Meteo's `zh` index,
resolves in one request, and never touches Nominatim.
