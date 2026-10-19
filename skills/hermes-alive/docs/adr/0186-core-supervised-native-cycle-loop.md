# ADR 0186: Core-supervised native cycle loop

Date: 2026-10-19
Status: focused real-Core integration passed; canonical packaging pending

## Connect existing ownership, do not install a second scheduler

`AutonomousHostRuntime.run` already owns cycle count, stop, interval and active
task cancellation. It now accepts an explicit optional `cycle_step` capability;
its default behavior is unchanged. `NativeCognitionHost.run` supplies its existing
`step`, so every turn binds current owner policy and a fresh operation-bound model
caller beneath the same durable identity/mode/cursor ownership. There is no second
loop, provider registry, timer daemon or delivery queue.

`NativeCognitionHost.start` explicitly delegates the coroutine to the supplied
Core `PluginContext.spawn_task`. It requires the running event loop and already
bound current Core profile; it does not find profiles or install a startup hook.
Duplicate scheduled/active starts reject. A refused start closes its unsubmitted
coroutine. On loop exit the native wrapper gives retained child leases a bounded
reaping opportunity; uncertain leases are not cleared or files deleted by fiat.

## Actual focused proof

`probe_alive_core_supervised_host.py` uses actual Core548e66f plugin context,
ownership ledger/unload, launch binder, config loader, native worker and AIAgent.
The Core task inherits profile context even after the parent's binder exits.
Only HTTP is controlled; the resource-limited container has no network. A held
native request makes cancellation observable rather than assuming the task was
active. Actual Core unload cancels the loop and worker; its ledger, worker scratch
and pending-call state become empty. The open durable cycle remains unclosed.

Reopening the consumed operation does not spend again or invent success: it
returns `cycle_failed`. Explicit owner pause closes that retained cycle without
inference; explicit reenable and a materially updated public observation complete
two bounded cycles. The second uses reconsideration without another generation.
No physical messages or actual model inference occur. This is not a clean real
recommendation round or production startup installation.

`run_native_supervised_host.py` covers callback/identity continuity, fresh callers
per cycle, duplicate starts, overlap, cancellation, retained cycle and refused
supervisor with a fake driver and supervisor. Portable CI runs that unit test;
the actual Core probe must be invoked separately against an explicit checkout.

## Remaining operational work, not an acceptance shortcut

Public startup is still not wired to run the experimental kernel. Synchronous
plugin registration is not a running event loop; actual Gateway lifecycle and
unload/upgrade/restart must be qualified before enabling it. Current consumed-call
recovery is fail-stop with explicit operator pause/reenable, NOT autonomous
transient-failure recovery. A future bounded, auditable recovery policy needs a
fresh causally linked operation, current authority and budget, without changing
the failed receipt or retrying an uncertain physical side effect. Do not call
this production-ready because controlled cancellation passes.

Host-owned source-read leases, useful source-grounded sharing, noise-resistant
long-term memory/agenda/adaptation, all-provider auth renewal, lifecycle/migration,
ten fresh complete clean rounds and actual production acceptance remain open.
No Core/production/model config, other plugin or wmw changes or real sends.
