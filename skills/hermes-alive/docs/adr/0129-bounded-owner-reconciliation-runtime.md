# ADR 0129 — Bounded owner reconciliation runtime

Date: 2026-10-14

## Composed host tick

`TransportReconciliationRuntime.tick` joins canonical owner binding discovery,
publisher/route resolution, current user policy, host-owned withdrawal and durable
observation consumption. One tick scans at most a configured number of bindings
and consumes at most one bounded page per binding; it never sends, drains FIFO,
calls a model or invents a delivery outcome.

Binding discovery filters the authenticated host-supplied subject in SQL and
rechecks canonical owner/source/actor/signature before invoking the trusted
resolver. Current policy must match its signed owner command and cannot ignore
a newer authenticated command because a cache is stale. Async resolution is
followed by another current-policy check; a pause during that wait can withdraw
the pending submission rather than using the earlier enabled flag.

Per-binding ordinary failures leave other bindings eligible. Returned failure
references are keyed owner/sequence pseudonyms with finite stage names, not raw
errors, body, destinations or credentials. Cancellation/BaseException escapes.
Async resolver/withdrawal operations use cooperative timeout/cancellation and do
not retry automatically. Synchronous SQLite/source qualification can still block,
and a callback that suppresses cancellation is not proven bounded by wait_for.

The returned ascending scan cursor wraps to zero at the current end so unresolved
old bindings can be revisited for late reports. The host owns scan-cursor storage
and invocation cadence. Restart from zero is safe because each binding's actual
consumption checkpoint is durable and idempotent. Empty source pages are not
delivery completion; no binding is retired based on guessed absence of effects.

## Evidence

Windows/fake and Linux actual stock Weixin constructor/send with only physical
IO replaced exercise an actual kernel lease/start and the enhance publisher:
unsigned bad binding before a valid one, another user's row excluded, bounded
scan/next cursor, reopen at the next page, wrap and revisit without another send,
failure isolation, opaque stable diagnostics, a cooperatively stalled resolver
that times out, explicit pause during async resolution and cancellation that
escapes rather than becoming an ordinary failed/retried tick. One start and zero
canonical delivery/learning outcomes remain. No production hook/timer is registered.

Linux final process exits 0, read-only current-file overlays, network none plus
audit guard, resource limits and --rm. No full source snapshot/clone or labelled
test container remains from this run. The retained base snapshot was reused, not
deleted. Production StartedAt is unchanged. Zero real model calls,
actual channel sends, private-history reads or production configuration/restart
changes occurred. These are isolated integration facts, not continuous human
usefulness, installed-package qualification or real transport delivery evidence.

## Remaining whole-system work

Implement host lifecycle/cadence/cursor ownership and authenticated control
admission, with per-owner observability and cancellation-safe shutdown. A global
pause affecting many bindings is not an atomic transaction in this batch API;
withdrawal may wait behind in-flight IO. Old bindings/retention need controlled
retirement and upgrades/recovery qualification, not unbounded forever polling.
Defaults and budgets need measured tuning rather than assuming the test values
are suitable for production. Full writer/performance/failure/restore qualification
remains open.

Connect this control/result runtime to the useful autonomous planning/expression
loop, canonical attributed feedback and real-model longitudinal evaluation.
Preserve layered memory/agenda, consent/erasure, model/channel inheritance,
portable fresh install/upgrade/migration/rollback and production acceptance scope.
Enhance's independent release/acceptance cleanup remains after Alive. The full
goal is not fulfilled by this bounded observation/control tick.
