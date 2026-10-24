# ADR0213 — Admitted Core controls and finite execution authority

2026-10-24 (Asia/Shanghai), Codex.
Status: implementation under isolated qualification, NOT production acceptance.

## Decision

Extend the existing `/alive` Core command with enable, pause and status. The
actual admitted source, exact persisted conversation and confirmed setup owner
must match before any control/state disclosure. A code or copied config hint is
not sufficient. Reset may retain the configured person/route but never restores
erased or prior-session discussion context.

Enable reuses the existing policy, truthful host snapshot, encrypted route,
signed delegation and native host. An actual enable command creates a structural
inbound-authority event, not a copied private chat. A full-envelope authenticated
activation references the confirmed setup and exact grants. Authorization defaults
to 30 days, at least one hour between starts and at most three starts daily;
confirmation guidance states these defaults before suggesting enable. Startup
reads valid authority and never renews it. Expired, paused, revoked or superseded
authority cannot become enabled through a config hint or legacy/shadow fallback.

The lifecycle has an explicit `kernel` engine for authenticated native execution.
`kernel-shadow` remains non-sending even when a prior unexpired activation exists;
both enable and trusted live attachment require the native engine. Preserve the
explicit engine through runtime uninstall/reinstall and use engine-appropriate
hook manifests/verification. Do not silently rename or promote shadow mode.

A fresh explicit enable may supersede an interrupted same-owner host intent only
after its owned task/children have settled. The new signed activation names that
exact prior open cycle; recovery may idempotently finish that authorized control
transition. Close the old host intent as paused, never as delivered/successful.
Do not erase outcome evidence, retry its physical send or close a newer cycle on
replay. Ordinary startup without such an explicit supersession still preserves
the interrupted operation identity. Physical model/tool cancellation and actual
daemon-crash recovery require their own evidence beyond a synthetic open-cycle test.

Require approved public queries before enabling this initial execution path.
Never inherit the operator's private interests as public defaults or silently
authorize private-chat/profile mining. The native caller and fallback registration
are shared with the existing shadow assembly and remain Core-owned. This live
path does not attach blanket CoreContextRead or automatic feedback learning merely
because model calls and public searches were authorized.

Only the existing standard executor may submit, with canonical Core parsing and
mandatory owning conversation continuity. REQUEST_ACCEPTED is local submission,
not remote delivery. Each HostCycle supplies a unique authorization operation.
The discovery preparation wrapper retains its original pending/reap capability;
no uncertain child is abandoned to replace a terminal generation. No second FIFO,
transport retry, provider router or Core edit is introduced.

Before public discovery or model work, use the same authenticated owner-wide
consumed-start history as the final atomic cadence reservation. The advisory
next-start calculation does not reserve or authorize a launch. A standard cycle
rechecks it and returns waiting_for_change while cooling down, without model
spend. Grant renewal cannot reset history; uncertain/error returns still count.
Keep final reservation in the existing writer transaction so concurrent advisory
reads never permit two actual starts. An operator pause enters the existing paused
cycle before route/tools/model work, rather than being reported as a model failure.

Pause revokes new work and sets the owning loop's cooperative stop. Cross-process
CLI disable revokes the same policy, not just legacy files. A real queued channel
message may still finish; do not claim that the channel has drained. CLI status
reports durable authority separately from unverified runtime liveness. Repeated
configuration confirmation/startup reuses an already-current continuity bridge
rather than closing a bridge that active send parameters still reference.

## Qualification boundary

Use installed candidate bytes, real Core CLI/discovery/command dispatch, signed
grants and actual task creation/stop/restoration. Initially stop before model/tool
work: this qualifies control wiring, NOT a full discovery/model/send cycle or a
daemon restart. Test foreign-owner refusal, no implicit private-read authority,
startup without grant renewal, paused startup refusal and original Core model
configuration preservation. Keep the full natural conversation, source utility,
longitudinal learning, interrupted-work recovery, legacy migration, fleet,
consumer installation, ten-round quality and separately authorized production
acceptance gates open. A callable new command does not close them.

## 2026-10-24 product lifetime decision supersession

ADR0214 supersedes this ADR's monthly expiry for ordinary proactive enablement:
the owner chose lasting authorization until pause or revocation. Both grant and
activation now require an explicitly signed persistent lifetime, not mere expiry
omission. Historical finite records keep their original meaning; no upgrade or
startup expands them. Scope, policy, route, cadence, cancellation and independent
retention controls above remain. This is not production/send authorization.
