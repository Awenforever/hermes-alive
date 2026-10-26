# ADR0241 — Guided delegation for clear ongoing assignments

Date: 2026-10-26. Status: implementation under isolated qualification.

## Owner choice and authority

Normal use accepts clearly assigned continuing work after first guided consent.
Per-item confirmation from ADR0240 remains optional. Ordinary conversation,
third-party quotations, tentative or negated intentions must not become tasks;
ask when unclear. The main agent interprets this distinction. No keyword parser,
second intent model or parallel whole-chat history is introduced.

`--confirm-explicit-followup-intake` stages a separate signed setup choice. The
summary discloses item retention using the selected duration. Existing setups
remain off; an upgrade cannot imply consent. `/alive intake off` stops new direct
intake, keeps existing items and clears transient interpretation tickets. `on`
requires the original guided grant; `status` reports the actual choice. This is
not contact enablement, permanent-interest learning or external-tool authority.

## Actual Core boundary

The existing collector binds canonical owner/profile/receiver/conversation,
configuration, task, turn and normalized current user text. Only bounded current
text is temporarily available, never persisted as a second chat history. The
Core tool dispatcher supplies turn/session correlation through its task-local
approval observability context, including deferred tool calls. This correlation
is not approval. Missing capability or mismatched context refuses direct intake.

`alive_agenda record` requires the current signed permission revision and an exact
current evidence span. Exact matching grounds attribution; it does not prove the
model's semantic interpretation. A newer main turn or canonical admitted input
invalidates late-response tickets, even while the next main turn is queued.
Normalized input replays do not repeatedly invalidate fresh tickets. No message
is consumed, reordered, sent or placed in Enhance's physical queue by this observer.

The host signs a source receipt with opaque request/evidence/turn fingerprints and
the specific configuration/permission revision. The proposal uses the distinct
`user_delegated` authority and system intake actor. It never impersonates a
literal owner-confirmed item. Projection/rebuild and cognition independently
verify the original protected grant and historical permission before the receipt.
Later revocation stops new intake without rewriting already admitted history.
Retried exact tool calls do not renew retention, restore erased content or
reactivate completed items. Dates are explicit and within the retention window.

Typed source context carries the original proposal authority and whether literal
owner confirmation occurred. Historical task details are not a verbatim user
message, current task state or a fresh execution grant. The same existing Native
agenda/decision/communication path handles the admitted item; default execution
still grants only share/ask, with no new external action capability.

Admission and cognition now use the same complete task-summary window. Do not
save a newly interpreted item that cognition would later silently omit for
exceeding its bound. Return an explicit concise-summary/split request while
preserving conditions and negation. Original proposal authority travels as
provenance outside that unchanged evidence window, rather than shrinking the
space available to historical task details.

## State and qualification

A saved active item is distinct from a running proactive host. Record/list tool
results report actual runtime status and explicitly do not establish delivery.
Saving a task does not start a paused or unenabled background host. The first
real-model experiment exposed an overclaim here; retain that evidence rather
than counting a successful record as proof that reminders were running.

Frozen r117 passes four actual-Core focused suites. Source-free coverage runs
both optional per-item confirmation and delegated intake through Core's actual
collector/tool dispatcher/commands and then controlled Native reminder/continuity.
It checks replay, wrong turn/evidence, permission revocation/regrant, superseding
turn, historical rebuild, completion, missing storage and erasure. Frozen r118
adds canonical admitted-input invalidation and source-receipt tamper checks;
r119 adds runtime-state fields. Their final qualifications are separate.

The first r116 integrated run failed because authority validation constructed a
second schema-initializing journal while the agenda projection held a write
transaction. `KernelSetupStore` now reuses an exact supplied journal after its
root/type/inventory checks. Retain the database-lock failure; do not weaken the
authority check or catch the failure as success.

Five actual inherited-main-model cases on r117 record one clearly assigned
synthetic task and create no proposal/record for casual, quoted, tentative and
negated cases. Ten provider requests complete, no external send occurs, and the
host is not enabled. Constraint/due evidence survives intake, but main wording
initially overstated reminder readiness. This is bounded synthetic evidence, not
exhaustive intent comprehension, actual delivery, longitudinal adaptation, fleet
or production acceptance. Sharing-quality remains0/10, a separate subgate.

## Current integrated qualification

Frozen r120 passes all four actual-Core focused suites, including manual and
delegated intake followed by controlled Native reminder/continuation, canonical
new-input invalidation, source-tamper rejection, no-grant refusal, explicit
oversized-summary refusal and original-authority propagation into actual model
requests and main followup context. Existing execution/discovery/paged continuity
regressions pass. These use controlled Native model replies, not real transport.

Two additional actual main turns on r120 use an ordinary request without naming
Alive and a tentative thought. Four inherited DeepSeek requests complete. The
request is directly recorded; the tentative thought creates no item. Returned
state and actual main response now correctly say automatic reminders are not
running while the host is unenabled. The response remains verbose and exposes
internal status labels; do not call it a completed natural interaction design.
Both model experiments closed with exit0, six-file credential audits finding no
match, removed projections and destroyed containers. No external send occurred.

The earlier full r118 run was intentionally superseded after the unified source
window/provenance changes; partial logs and the explicit cancellation are kept.
It is not a full pass. Full r120 portable regression runs separately and must be
checked for its real terminal state. Cold-process followup, ordinary revisions,
natural completion/cancellation, non-communication actions, outcomes/adaptation,
four-target distribution and production acceptance remain open.
