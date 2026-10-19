# ADR 0187: Refresh the host-owned Core profile scope per cycle

Date: 2026-10-19
Status: real Core rotation comparison passed; composed/packaging checks pending

## Evidence changes the startup sequence

Core task creation copies the parent's current context. A long-lived task created
inside the startup scope keeps that secret mapping, even after the parent exits
and the user rotates `.env`. Per-call mapping-identity checks cannot detect a
change to a file which Core has not reloaded into that mapping. This is not a
provider failure or reason to add an Alive credential store.

`probe_alive_core_cycle_scope.py` runs the real Core loaders and native host loop
with a controlled cycle driver. In both launch and routed profiles, two cycles
with only the startup scope read the initial synthetic key twice. With a fresh
Core scope each cycle, the second reads the rotated value. The parent startup
mapping is restored, environment bytes unchanged and foreign effective homes or
explicit foreign stamps rejected. This is actual configuration/acquisition
evidence, not an HTTP or model-intelligence test; its driver makes no model calls.

## Decision

`NativeCognitionHost` accepts an explicit optional async `profile_scope` factory.
Each `step` enters it around the entire operation, including fallback/client
lifetime, and releases it on success, failure or cancellation. Callers which
already own fresh per-step scopes can omit it; background embedding must supply
the appropriate current host scope. The durable loop and current-policy/model
capability checks remain unchanged.

`core_profile_cycle_scope` accepts only an explicit existing home matching the
current Core context. An explicit foreign stamp rejects before loaders run.
For the process's launch home it asks Core's `launch_secret_scope` off-loop and
installs the prepared mapping through Core's `_profile_runtime_scope`; Core's
legitimate env-only launch credentials survive. For a routed home it delegates
to Core's `_async_profile_runtime_scope`. Alive does not enumerate credentials,
parse dotenv, change environment precedence, invent provider keys or resolve its
own model routes. The native caller still exports only explicitly granted names.

## Composition and limits

Portable supervision tests assert one scope entry/exit per cycle and release on
cancellation. The actual Core-supervised native-worker probe now supplies this
scope factory, so final packaged qualification must repeat its real unload test.
Its model HTTP remains controlled and network disabled. Neither probe is a fresh
real recommendation round or all-provider token renewal qualification.

Actual Gateway startup wiring remains pending: synchronous plugin registration,
disk lifecycle hooks and per-profile context ownership must be connected without
guessing a global manager or running two engines. Key refresh is a prerequisite,
not a substitute for this installation work. Bounded automatic failure recovery,
host read leases, useful fresh sharing, long-term memory/agenda/outcomes, portable
lifecycle/migration and production acceptance remain required. Production and
other plugins are unchanged; no automatic experimental startup is enabled.
