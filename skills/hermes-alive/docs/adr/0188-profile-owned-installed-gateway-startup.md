# ADR 0188: Profile-owned installed Gateway startup handoff

Date: 2026-10-19
Status: focused actual Core startup/discovery passed; final packaging pending

## Concrete handoff

The actual plugin `register` now retains a `GatewayHostBinding` in its own
Core-loaded module generation and registers unload cleanup. There is no global
profile registry or guessed default manager. Trusted host assembly calls
`configure_kernel_gateway_host` with the current profile's explicitly bounded,
per-cycle-scoped native shadow host. Live execution is refused by this boundary.

The dedicated `kernel_gateway_handler.py` is a disk lifecycle adapter: on
`gateway:startup` it obtains Core's current profile manager, checks exact scope
and the enabled `hermes-alive` module, then invokes that module's startup binding.
It never imports or starts the legacy watcher or mutates environment/sys.path.
Missing assembly is `not_configured`, not success or fallback to a second engine.

One plugin generation starts at most once. Duplicate startup events do not spend
again, even after its bounded task completes. Unload closes only that instance;
an old callback cannot tear down a new generation. Core owns task cancellation.
Cross-profile native attachment, current-profile active legacy watchers and an installed
canonical legacy handler refuse new startup. These guards cover the current
owned legacy contract, not every possible fork or external process. Actual
legacy-to-kernel migration/restart still needs qualification.
On Python without public Task.get_context, a named legacy task cannot be proven
foreign and conservatively blocks native startup; do not guess its profile.

## Actual evidence and limits

`probe_alive_installed_gateway_startup.py` copies the actual repository plugin
and dedicated adapter into two disposable Core profiles. Real Core548e66f
discovery/import/register and disk HookRegistry dispatch are used, not replaced.
No synthetic PluginContext is substituted. Both profile modules are distinct;
missing assembly, foreign attachment, duplicate event, actual in-flight unload
and stale module callbacks have explicit assertions. A routed profile completes
a native shadow cycle. The launch profile is unloaded during a held actual native
worker request; pending/workspace/task registration clear without closing its
interrupted durable cycle. Model HTTP is controlled and the container has no
network, inference or physical messages.

This proves the lifecycle handoff with explicit trusted test assembly. It does
NOT prove automatic host assembly, normal installer selection, fresh PM dependency
provisioning or semantic recommendation quality. Core discovery warns that the
retained interpreter lacks declared PyYAML/tzdata; this code-copy experiment does
not install them or qualify a new-user environment. Preserve that limitation.

The legacy lifecycle installer still chooses the legacy handler. The new adapter
is not silently enabled in existing installations. Real onboarding/config-driven
assembly and mutually exclusive engine migration remain next, followed by host
read leases, bounded automatic recovery, useful sharing and long-term memory/
agenda/outcome evaluation, portable lifecycle/migration and production acceptance.

`run_gateway_host_binding.py` adds source-only generation/profile/legacy guards;
it does not replace the actual installed Core proof. Existing source tests must
copy the added plugin module and provide Core's current ownership contract.
The local admitted-inbound suite cannot run encrypted cases without cryptography;
use the retained managed interpreter rather than install into the user's Python
or weaken encryption. Final archive qualification must run both actual Core
startup/legacy regression and the portable suite before retaining this candidate.
