# ADR 0130 — Host-invoked autonomous cycle composition

Date: 2026-10-14

## Composition

`AutonomousCycleRuntime.cycle` joins the existing result/control reconciliation
runtime with current user policy, discovery-to-intent planning, natural expression,
send-time authorization and qualified publisher submission. The host supplies
authenticated owner, operation identity, configured-model callbacks, existing
user grant/route and qualified channel callbacks; this module manufactures none.
Current planning policy is taken from canonical user-owned state, not supplied
by a model or arbitrary caller context.

Paused owners reconcile old work without spending on new model calls. Unresolved
reconciliation failures return an explicit attention disposition, not silent
success or another send. Shadow is the default and invokes expression only:
it creates no action attempt, lease or delivery authority. Explicit execution
requires the host execution contract; silence/denial never dispatch. Proposed
actions use the existing prepared-attempt checks and publisher execution seam.

The prior generic outbox acquisition chooses any eligible attempt. New optional
owner/attempt selectors make cycle acquisition exact under the existing writer
lock rather than claiming another worker's unrelated eligible work. Invalid
selectors reject before outbox reconciliation. Default generic acquisition behavior
and existing authority/expiry housekeeping remain unchanged. Other started or
uncertain attempts are not restarted by this integration.

Repeat completed planning/expression operations use existing authenticated replay.
If the prepared attempt has already started, exact acquisition yields unavailable
and cannot send again. This is not proof that the earlier message was delivered.
No lifecycle timer or production hook is automatically enabled.

## Evidence and scope

Exact-acquisition test covers wrong owner, missing attempt, reclaimed expired
lease, matching generation increment, contention and invalid selector rejection.
Existing dispatch cadence/authority regression passes after the SQL selector change.

Windows fake transport and Linux actual stock Weixin constructor/send with only
physical IO replaced exercise a fresh cycle operation on an existing synthetic
discovery source and explicit user delegation: planning/expression/preparation/
authorization/submission; queue observation; reopen with provider calls forbidden,
no additional model spend and no duplicate start/send; independent shadow cycle
without another action attempt; deliberate silence; explicit pause reconciling
the old queued work without a new model call or physical send. Native transport
may split the expression into multiple queued chunks and all are covered by the
publisher association, not a forced one-bubble transport change.

Model calls are controlled synthetic fixture replies, including positive semantic
reviews. They demonstrate composition/replay, NOT semantic judgment, independently
qualified source grounding, actual model performance or user benefit. The fixture
setup already runs one unused expression operation; the composed cycle uses a
fresh operation identity so its planning/expression are not merely a warmed result.

Linux exits 0 with network none plus audit guard, bounded resources, read-only
current-file overlays and --rm. The retained base snapshot is reused; no full new
snapshot/clone or labelled test container is left. Production start time is
unchanged. No private-history read, real model call, actual channel send or
production configuration/deploy/restart occurred. Public release and enhance
final acceptance remain unchanged.

## Next whole-system qualification

Host lifecycle/cadence/cycle allocation and scan-cursor storage are still absent.
Fresh-install/onboarding and model/channel inheritance must construct real qualified
callbacks without personal defaults. The current publisher path is Weixin-specific,
not evidence that every Hermes channel is supported. Synchronous work, cancellation,
provider budget/lifetime, source upgrade/paired migration/restore, deferred deadlines
and global pause across outstanding bindings need further qualification.

Real main/backup model families do not automatically constitute independent semantic
review; the earlier unsupported-claim findings are not resolved by this synthetic
positive reviewer. Qualify useful multi-cycle behavior on fresh public/synthetic
scenarios with actual configured models and bounded inputs, including silence,
novelty, persistent agenda, memory corrections and controlled feedback. Connect
canonical attributed outcomes/reflection only with sufficient evidence. Portable
installation/upgrade/migration/rollback and real production acceptance remain
required. The full goal is active, not achieved by this composed prototype.
