# Hermes Alive — Development Memorandum

Internal engineering notes. User-facing README files describe the product;
failure history and non-regression constraints live here.

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
