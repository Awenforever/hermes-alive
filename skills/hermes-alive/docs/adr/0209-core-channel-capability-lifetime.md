# ADR0209 — Acquiring a channel is not routing or sending authority

Date: 2026-10-23 (Asia/Shanghai).
Status: development implementation, focused actual-Core qualification passed;
ordinary live assembly remains pending.

## Integration decision

Use the documented `PluginContext.register_platform_handler` and Core's own
profile-scoped configured platform inventory. Do not hardcode WeChat or a platform
list, patch `connect`, intercept private chunks or discover a random global bot.
The opted-in shadow plugin registration now acquires these capabilities through
GatewayHostBinding; the legacy default remains unchanged and no sender is started.

Each handle belongs to one immutable profile home and plugin generation. The
factory captures weak references to the standard adapter and its actual Gateway
loop. A callback is not readiness: it can run before the adapter connects. Access
requires the owning home/loop and a currently connected adapter. Disconnect or
garbage collection refuses access; replacing a disconnected adapter is allowed.
Two still-connected adapters are ambiguous, not "last callback wins": fence the
handle until a new host lifecycle rather than possibly choosing another account.

Unload closes references, never the Core-owned transport, other plugins' work or
the physical FIFO. Retained old factories cannot revive a closed handle. Current
Core dedup still prevents same-qualname hot-reload acquisition; do not mutate it,
invent new qualnames or report a skipped generation as ready. A full new Gateway
lifecycle must really occur when required. No production restart is authorized.

Capability failure is observable by its sanitized class, without config, token or
raw exception text. Non-sending shadow cognition may continue without a channel;
future live assembly must not interpret this as permission or transport readiness.
Plugin isolation is not silently disabled to gain an adapter handle.

## Qualification

Pure tests cover before-connect acquisition, current connection, disconnection,
replacement, ambiguity and persistent fencing, wrong platform/home/loop, unload,
stale callbacks, invalid names and weak-reference collection. They run on the
Windows execution host and managed Linux Python without pretending a simulated
OS is native installation acceptance.

The actual-Core test uses v0.22.5 read-only supply, its real config loader,
PluginContext, PluginManager, BasePlatformAdapter factory wiring and unload. An
isolated profile config enables the experimental path; the inventory is compared
with Core's actual loaded config, not a frozen platform count. An in-memory
transport raises if send is called. Connect/rewire/disconnect/reconnect/unload,
same-generation dedup refusal, fresh-manager/fresh-adapter recovery and foreign
scope refusal pass. The plugin unload leaves the Core adapter connected.
Saved wrapper exit0; disposable container removed. No models, real messages or
production changes. This does not qualify a real Gateway daemon or transport.

Separately the preceding standard execution tree
`1fd5be7841260d6c8ec123c4022a99a3fbf74411` now has full portable CI exit0 and 84
suite logs. That result is not inherited by this acquisition delta or the later
two standard-route guards. A fresh current-Core dependency build is a distinct
prerequisite, through Core PM in an empty isolated environment with no credential
or production mounts. A retained interpreter cannot serve as that proof.

## Remaining ordinary activation work

This component only obtains a scoped adapter. It cannot choose a recipient,
manufacture Core receiving-bot/thread/workspace metadata, infer user approval or
make a model-written destination authoritative. Reuse Core's canonical routing
and existing exact route/owner authorization; no default-bot fallback or third
routing algorithm. Shared-bot/profile routing is still unqualified.

Before enabling the ordinary path, resolve profile/principal and route ownership
explicitly. Existing experimental owner helpers based on a raw user ID alone are
not evidence of cross-platform identity equivalence; equal IDs from different
platforms/workspaces must not silently merge people or grant access to memory.
Preserve legacy identities/history and require an explicit supported transition,
not a guessed reassignment. This is a live-onboarding prerequisite, not permission
to rewrite current private records.

The distinct fresh dependency qualification has exposed an old plugin declaration
that needs forward compatibility: current Core's lock selects cryptography50.0.1,
whereas Alive demanded equality to50.0.0. Accept the supported50.x API range rather
than forcing either a newer patch floor or a host downgrade. Keep exact CI pins
for reproducibility; actual PM resolution/install remains a separate pending proof.

Also separate durable user permission and stable host contract from a transient
connection: disconnect/reconnect must not manufacture a new user grant or silently
revive revoked authority. Complete guided setup, the actual consumer loop and
feedback, migration/rollback, fresh managed installation and real platform matrix.
Keep quality streak0/10 and the complete objective; do not present passive channel
acquisition or another preview as the finished Alive product.

## Later actual-discovery finding — supersedes inventory acquisition above

2026-10-23: the first focused tests instantiated a context directly and did not
exercise the full plugin discovery parent/worker lock relationship. Actual
public discovery exposed a deadlock in the original load_gateway_config call:
configuration materializes a deferred platform whose loader needs the discovery
lock held by the parent waiting for Alive registration. Both failed fixtures and
the actual worker/parent stacks are retained; the private-loader failure alone
was not treated as sufficient product evidence.

The correction obtains Core enum names plus public registered_names(), which
does not import or resolve deferred adapters. A post-discovery Core listener
adds platforms that registered later in the sweep. Its unsubscribe handle is
owned by the plugin and disposed on manual close and unload; a retired binding
cannot recreate handles. Known inventory may include inactive channels: only
a connected, current scoped handle can be used. No channel is enabled by this.
This replaces the initial full-config inventory mechanism, not the ownership,
permission, transport, hot-reload or final consumer acceptance constraints.
