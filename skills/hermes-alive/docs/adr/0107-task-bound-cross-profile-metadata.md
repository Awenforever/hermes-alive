# ADR 0107 — Profile-local caches cannot bridge routed admission

Status: revised research handoff qualified against actual scoped SDK dispatch;
not registered by Alive's real runtime or promoted to feedback authority.

## Counterexample to ADR-0106's single-profile success

Actual Hermes caches plugin managers and directory-plugin modules separately
for each resolved home. A pre-dispatch callback under a transport home and a
post-admission callback under a routed runtime home see different fixture cache
instances. The new actual SDK scope probe fails: the destination observation is
null rather than the staged quotation. A synthetic test that merely changes a
profile string inside one cache would not detect this. Do not expand the cache
into an identity-only process-global pool; separate receiving bots can reuse
wire identifiers, and a post callback must not consume another task's evidence.

## Revised research handoff

TaskAdmissionMetadataHandoff uses a private attribute on the current asyncio
Task, not on a MessageEvent, gateway/session handle or global profile pool.
Synchronous callbacks in Hermes' actual async dispatcher run inline. The same
message task can therefore retain its bounded private state across profile scopes
and separately loaded fixture classes. A child/other task does not inherit that
attribute. Missing/current-task changes fail closed; there is no identity-only
fallback. No event object, message body, credential or raw sender/profile identity
is retained. The cache's nonce binds the normalized target runtime home as HMAC,
plus the existing exact source/message/text identity. Paths are normalized
lexically without filesystem I/O.

State is single-entry per task, with a bounded number of pending tasks per
origin handoff instance. Wrong target home, duplicate intake, rewrite or invalid
metadata remains unavailable; a scope change poisons the current handoff rather
than reviving its old scope. The receiving profile consumes and clears the origin
state without a shared plugin module or registry patch.

Timers clear the state independently of subsequent messages while the event
loop runs. Task completion/cancellation also clears and cancels the timer.
Consumption removes its completion callback as well as the timer, preventing a
reused long-lived task from accumulating cleanup callbacks. Both scheduling
sites use empty Context objects: default callback-context copying would retain
the caller's profile secret/session ContextVars even though the explicit cache
contains no credentials. Tests check empty callback contexts with a synthetic
private-context sentinel. Suspended/stalled loops are not a hard real-time erasure
guarantee; production shutdown/reload/suspend qualification remains outstanding.

## Actual evidence and scope limits

The first scope probe uses actual _profile_runtime_scope, plugin-manager
discovery, the real GatewayRunner runtime-home resolver and post-admission SDK
dispatcher. Its source carries a SYNTHETIC pinned RoutingIdentity containing two
disposable homes. This proves real scoped dispatch/module separation, not live
canonical routing resolution, transport authentication or full _handle_message.
No runtime resolver is mocked, but the identity it reads is synthetic.

Failing snapshot d7c92214ff4541d7c292a40eddcc421c601a601b, archive SHA256
791c05866a36ab9cac657f8aebec45102a1afdf2e4aa1eab08f2eebf1dee5157;
alive-metadata-profile-offline-20261014-r1 exits 1 on the lost handoff assertion.
Corrected snapshot 0b54c137df4ce2884190b2dd10fcf5643e0c709a, archive SHA256
31af1b711df73557ab31f5b438a7bd543f74d79ef688f6487a62e9140455dbe3;
alive-metadata-profile-offline-20261014-r2 exits 0 for task cleanup tests and the
actual scoped SDK probe. Distinct actual managers now recover the quotation only
in the routed runtime home; the transport home has no post-observation file.
alive-metadata-profile-auth-offline-20261014-r2 also exits 0 for the prior actual
auth/pairing/revoke/bot/rewrite probe using task mode. Rewritten input still
produces null metadata, and no outcome/learning is created.

Windows and Linux task tests cover cross-instance consume, other-task denial,
per-instance capacity, wrong scope, scope poison, rewriting, duplicate intake,
actual short loop timers with no later cache operation, successful task teardown
and cancellation. Timer/completion contexts and completion-callback removal are
also checked. Earlier cache tests still pass. The actual Alive callback remains
unchanged; the new path is used only by the disposable fixture.

The carrier still warns about declared PyYAML/tzdata installation gaps. All
containers are network-none, resource-bounded and mount only test scratch read
only; no production/wmw/other-plugin/restart/model/config/channel change, private
chat reads, real sends or live model calls. Real-call totals remain 95 logical /
107 HTTP attempts. Public main/version/README remain unchanged.

## Next action, without narrowing the objective

Test real canonical live routing identity, async callback/task behavior and
delayed/busy/replayed/disconnected inputs under the full gateway session path.
Verify a staged target against owner/channel-scoped canonical delivered history,
and handle absent adapter quote information explicitly, before Alive can use it
as attributed feedback. No quotation, author bit or task provenance grants
learning/action consent. Useful sustained agenda, calibrated model semantics,
layered/external memory, transitive forgetting, portable lifecycle/upgrade and
rollback plus actual production acceptance remain the complete Alive goal.
