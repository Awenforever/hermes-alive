# ADR0207 — Qualify ordinary channel integration against the actual Core lifecycle

Date: 2026-10-23 (Asia/Shanghai).
Status: investigation with actual isolated evidence; runtime activation pending.

## Problem and scope

The installed new kernel is explicitly shadow-only. Its executing research cycle
uses an optional WeChat-specific receipt publisher, and its older observation seam
requires a private chunk method. Neither establishes ordinary multi-platform
operation. Do not solve this by flipping execute, requiring Enhance, building a
second physical queue, or claiming a named method guarantees a safe integration.

Inspect the actual supported stable Core, qualify the smallest suitable existing
contract, then connect the existing authorization, outbox and supervised lifetime.
Do not add reviewer/framework layers while this product gap stays open.

## Source baseline and observations

Read-only supply baseline: Hermes v0.22.5,
`bf0203a794a07aac3ff764972ab9087baa4e4f4e`. This is a research clone, not a
production upgrade or a fresh managed-dependency admission. No Core edits.

- `PluginContext.post_message` / `apost_message` address the calling session,
  not a named persisted background recipient. `gateway/plugin_messages.py::_fit`
  truncates over-limit text rather than preserving the whole reviewed body.
  It must not silently replace the autonomous exact-body contract.
- `post_gateway_admission` receives normalized snapshots, not a Gateway handle.
  `pre_gateway_dispatch` has a handle but runs before authorization. A source
  identity or an adapter reference is not a grant to contact its user.
- `ctx.register_platform_handler(platform, factory)` exposes `(native, adapter)`
  through a documented public registration. Its registry is profile-home scoped.
  Connectivity, current generation, route ownership, threading, platform rendering
  and delivery still need separate behavioral qualification.
- `BasePlatformAdapter.send` is the platform-owned outbound seam. A transport
  result is not proof of receipt/read, and no model name may be inferred from
  ambient configuration. Reuse the existing canonical expression provenance.

## Actual no-network experiment

The experiment imported the real baseline PluginContext, PluginManager and
BasePlatformAdapter. Only the concrete transport was an in-memory subclass;
its connect method called the real Core factory-wiring implementation. Isolated
synthetic profile homes, zero model calls, zero real messages. No monkeypatching
of registries, lifecycle methods or dedup state.

Initial operation exited **1**: it incorrectly expected a new adapter to bind the
replacement after targeted plugin unload. Preserve that failed assumption.
The successor explicitly exercised the counterexample and exited **0**:

1. The factory runs before `is_connected` becomes true. Capturing a handle is not
   readiness. Repeated rewiring is idempotent; reconnecting the same adapter with
   a `None` native client does not rerun its factory.
2. `ctx.on_unload` retires the diagnostic holder. Targeted unload retains its old
   platform factory. A new factory with the same `(plugin, qualname)` is skipped
   on both the existing adapter and a replacement adapter: the retained old one
   claims the key first. The holder's closed guard prevents revival.
3. Full manager unload clears the factory registry, but an existing adapter still
   has the wired key. A clean registry plus a fresh adapter binds the active
   generation; this models relevant boundaries of a Gateway restart, not a
   real restart acceptance test.
4. Actual Core home scopes resolve separate managers/factories. A stale diagnostic
   callback invoked under a foreign home does not replace the owning handle.
   This does not qualify shared-bot satellite routing or recipient authorization.
5. The public send seam passes 10,278 synthetic characters, thread and interim
   metadata exactly into the fake transport. Actual platform rendering, chunking,
   remote delivery, media and Enhance FIFO are **not** tested by that assertion.

The experiment is a controlled component proof, not a new runtime feature or a
clean quality round. Both disposable containers terminated and were removed.

## Decisions and next implementation constraints

- Keep the new installed kernel non-sending until ordinary authorization, routing,
  submission/outcome interpretation and feedback are assembled and qualified.
- Do not bypass Core dedup, mutate its registries, invent varying factory names
  to accumulate stale registrations, or silently disable plugin isolation.
- Do not promise hot reload. An update needing a fresh Gateway lifecycle must
  report that requirement and remain not-ready until it has actually occurred.
  No production restart is authorized by this ADR.
- Resolve explicit recipient/profile/receiving-bot/thread through the host's
  canonical routing contract; never fall back to the default bot or home channel
  when an owned handle is absent. Shared-bot routing remains unqualified.
- Reuse Alive's exact-body, current authorization and single-start outbox. Alive
  must not split, retry or drain a physical transport queue. Enhance remains
  optional and owns its negotiated WeChat FIFO/token/retry responsibilities.
- Do not disguise an adapter result as a CLI or transport-delivery receipt.
  Unknown outcomes after cancellation/error must not become automatic resends.
- Test the actual committed consumer artifact with current managed dependencies,
  real native platform lifecycles and migration/rollback. These component results
  cannot enlarge the manifest's supported Hermes range by assertion.

Separately, a recent real resource-discovery cycle was factually supported yet
did not establish recipient attention value. Preserve that sample-scoped feedback
without a permanent negative interest tag, forced transcripts, hype, keyword
patches or an additional judge. Quality streak remains **0/10**.
