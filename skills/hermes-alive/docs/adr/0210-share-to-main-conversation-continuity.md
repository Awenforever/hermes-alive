# ADR0210 — An initiative must remain a conversation

Date: 2026-10-23 (Asia/Shanghai)
Status: accepted product requirement; implementation and qualification pending.

## Defect and verified limit

An independent authoring call can create a useful proactive share while the
receiving Hermes conversation knows nothing about it. A subsequent ordinary
question then produces confusion or unsupported improvisation. This is a product
failure, not merely a missing feedback record.

The current standard-channel execution branch calls the host-resolved adapter
and records a bounded adapter-return observation. That code does not bridge the
exact sent share and its supporting material into the main conversation. Alive's
encrypted history, source store and admitted-inbound observer are not proof of
that bridge. The new kernel is still shadow; no production fix is claimed here.

## Required behavior

- Follow-up should work naturally without a quote or special command when the
  referent is clear. A quote should select the corresponding share, not simply
  the latest one. Ambiguous referents require a concise clarification.
- Preserve the exact outward content and its relationship to sources, what was
  actually read, evidence limits and time. The main agent must distinguish a
  source-backed statement from an Alive interpretation and must not pretend it
  read or watched unavailable material. Further authorized research can extend
  the discussion; the original short share need not contain an entire source.
- Bind continuity through Hermes' canonical profile, receiving account, user,
  conversation and thread routing. Never inject into whichever session happens
  to be current. No cross-user, cross-profile or cross-thread disclosure.
- Use supported host conversation/context facilities; do not patch Core, invent
  a user turn, automatically start an agent task or interrupt an unrelated task
  just to deposit context. Sending, persistence and retrieval must be coordinated
  explicitly rather than assumed from an adapter call.
- Keep prepared, queued, accepted, failed, uncertain and confirmed outcomes
  distinct. An unsent draft must not appear as something the user has seen;
  a local send return must not be relabeled remote delivery. Recover safely from
  a crash between submission and context recording without resending a share or
  fabricating a successful history entry. Observed user quotations can supply
  additional evidence without retroactively rewriting an uncertain send.
- Retain grounding durably under existing permission, expiry and erasure rules.
  Follow-up after an ordinary Gateway restart should not depend on a worker's
  process-local memory. Respect an explicit conversation reset and do not
  silently restore erased or unauthorized content as permanent user memory.
- Keep Alive's initiative/grounding ownership separate from the host conversation
  and WeChat Enhance's physical FIFO/token/retry ownership. No second FIFO and
  no requirement that Enhance be installed for basic conversational continuity.

## Bounded implementation direction

Reuse the existing share identity, protected content, source references and
outcome journal. Qualify a host-native conversation bridge plus bounded relevant
grounding retrieval at the next admitted turn. Do not build a second chat engine,
copy every source into every prompt or add an unbounded new memory service.
Choose the concrete integration only after checking the actual supported Core
facilities and lifecycle. A diary or a mocked retrieval alone is not acceptance.

## Qualification

See RELEASE_ACCEPTANCE.md's continuity gate. Evidence must include the actual
main-agent response and the context/grounding it received in a consumer-installed
environment, not merely an Alive component assertion. Real external sends still
need separately scoped permission. No passing round is claimed by this ADR.

Bounded seam evidence (2026-10-23): actual Core v0.22.5 hook dispatch and turn
API-content composition, in a fresh PM dependency environment, preserve the
owning profile/session context and leave history/system-prefix bytes unchanged.
Foreign/cleared session and delegated-child cases supply no context. No model,
external send or extra agent turn ran. The experiment used a synthetic supplied
context; it does NOT establish authenticated Alive persistence/retrieval, source
grounding, actual consumer installation or a natural main-agent response. The
documented pre_llm_call return channel is viable; blindly appending a delivery
mirror into the transcript is not adopted as a substitute for the product gate.

## 2026-10-24 scoped-route implementation checkpoint

gateway_session_bridge and the owning GatewayHostBinding now provide exact Core
conversation snapshots, a canonical adapter/metadata resolver for the existing
standard-send interface, and scoped principal derivation. Actual v0.22.5
SessionStore, routing identity and GatewayRunner helpers are used; no Core edit,
new routing algorithm or latest-chat/default-bot scan. Native message history is
not modified and no user turn, model call or send is initiated by scope capture.

The fresh PM component experiment passes standalone lookup, unmodified origin,
native Telegram/Slack metadata, wrong owner/home/platform/thread/receiver refusal,
thread-local hook-envelope checks, cold-store reopen, disconnect/reconnect, reset,
unload and a multiplexed runtime with two possible bots. The receiver remains
authoritative even when the runtime's own different bot is online. Missing
persisted multiplex provenance refuses rather than guessing. Scope reads can run
on the Core hook worker; actual submission resolution requires its Gateway loop.

Principal v2 distinguishes platform, receiving profile and workspace under the
existing per-installation identity key. Physical home paths and conversation IDs
do not define a person; historical raw-user-ID subjects are not silently merged,
deleted or reassigned. These scopes do not grant content access or authorize IO.
The experiment uses synthetic peers/transport and partially constructed actual
Core objects, not a real daemon or consumer install. Retention/onboarding, exact
share/source/outcome persistence, the actual main-turn reader and full natural
follow-up qualification remain pending. This does not close the product gate.

## 2026-10-24 protected share and native main-turn reader implementation

The standard channel path now accepts a trusted continuity capability before
adapter IO and rechecks dispatch/home authority afterward. ShareContinuityStore
retains exact content, private Core scope, original source references and erasure
dependencies under explicit outbound consent, in the existing protected vault.
A signed structural share_prepared event binds the authenticated dispatch start,
scope and original retention horizon. It is not sent/delivered/viewed evidence.
Only a separately signed existing adapter observation supplies its truthful
success/error/unknown report; missing/exception/crash evidence stays unconfirmed.
No observer creates IO, an acknowledgment, retry, physical queue or user turn.

CoreShareContinuity attaches through the owning GatewayHostBinding and exact
CoreSessionRouter. The real pre_llm_call reader gets bounded protected content
and source grounding under the admitted turn's scope, never a latest session or
another profile/bot/thread. The context distinguishes sourced evidence, Alive
interpretation, actual reading limits and submission uncertainty. Ordinary
unrelated turns must not be forced into discussing it. Capture is optional for
older component executors; final ordinary live assembly must require the complete
conversational contract instead of silently enabling one-way dispatch.

Historical retrieval does not re-run current planning or expired executable
selection. Source retention expiry leaves separately consented exact outward
history with grounding unavailable. Explicit erasure invalidates dependent
content; an authorized durable subject-forget request stops disclosure even
before its physical worker finishes. Retention OFF stops new capture, not earlier
consented history. No raw scope/source/body is copied into the public journal.

The first immutable operation exercises actual current-Core routing/dispatcher/
turn collector with synthetic planning and adapter returns, reopened protection,
scope/clearance refusals, absent consent, failure and unknown effects. Standard
send, routing, startup and public plugin registration focus also pass. Expanded
expiry and pending-erasure checks use a new immutable operation. This is code
and component evidence, not an actual main-model answer, daemon restart,
compaction, exact older-quote recall, migration, consumer installation, natural
quality round, ordinary enabled operation or production deployment. Those gates
remain required; no quality pass or release qualification is granted here.

## 2026-10-24 actual main-agent diagnostic, still not the installed product gate

The opt-in probe uses an actual AIAgent.run_conversation, with Core-owned model
and fallback resolution, no tools/private chat/context files, empty supplied
history and no system/share prompt overlay. Actual pre_api_request observations
must show the exact protected share in the native current-user sidecar and not
in the system/assistant messages; a foreign thread must not receive it. Keep
complete original responses for semantic examination, not only the observer's
structural assertions. Projection/report paths are operator-supplied private
storage, and this diagnostic cannot silently run in ordinary CI/installation.

Initial operation r5 failed before a main model call because the probe assumed
a mapping rather than Core's actual VersionInfo object. The original trace is
preserved. Operation r6 uses the real version object and completes three main
turns: a clear unquoted question is answered from the exact share, excerpt-only
reading is acknowledged, and another thread asks for missing context. All three
activate the configured official fallback; Core labels the main route rate-
limited. Six main-request hook events do not prove six physical HTTP attempts
or successful use of the primary. No production/model configuration is changed.

Review also exposes an unwanted internal-field inventory in the reading-limit
answer. The context contract now marks bookkeeping as non-user-facing and
represents absent collector scope as unknown. It does not rewrite the model's
answer, add topic/word-specific rules or misrepresent original reading depth.
The changed candidate needs its own qualification. This remains an isolated
synthetic Core fixture, not ordinary live activation, an external send, consumer
installation, restart/compaction/older-quote qualification or a clean quality
round. The original full product and ten-round gates remain open.
