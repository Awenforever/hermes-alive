# ADR-0028: Host capabilities and routes are separate authority

Status: accepted for the shadow kernel

## Context

A destination-free action contract prevents model-authored route injection,
but it does not answer which Hermes installation, profile, platform and chat
may execute the action. Nor does the existence of a send-shaped function prove
what its return value means.

We audited the official stable `v0.21.6` source at commit
`f27cdbce5ab63eafe8633b293a75151409da5769`. Its public
`PluginContext.inject_message()` contract explicitly says that `True` means a
host accepted the request, not that the turn completed. The gateway's
`BasePlatformAdapter.send()` does return `SendResult`, and final responses use
a delivery ledger, but neither direct delivery nor that terminal receipt is
currently exposed through `PluginContext`. Reaching into the gateway runner or
its adapter map would make Alive dependent on private implementation state.

## Decision

Alive represents the host boundary with two independently authenticated facts:

1. a host capability snapshot names the Hermes version, public plugin API
   contract, interface, availability and strongest truthful receipt level;
2. a route binding names the subject and capability, references the exact host
   snapshot, and stores the user-selected platform/profile/chat locator only in
   the encrypted content vault.

Creating a route requires an exact prior user event authorizing that binding
ID. The durable journal receives only a keyed route fingerprint, encrypted
content reference and structural identities. A new host snapshot makes routes
bound to the old contract stale; explicit route revocation takes effect
immediately.

Send-time authorization requires a current route whose public interface can
prove `external_delivered`. It binds the route event, snapshot and authenticated
route descriptor into the short-lived permit. Outbox materialization and
`begin_execution` revalidate those facts. The execution grant returns the
normalized action and decrypted route only after it durably records
`dispatch.started`.

The current official `PluginContext.inject_message()` is therefore represented
as `request_accepted`, not `external_delivered`, and cannot activate live Alive
dispatch. The bridge stays disconnected until a supported interface and its
truthful receipt semantics are qualified. ADR-0054 corrects the broader
inference that this necessarily requires a new upstream API: the public
`hermes send` CLI is an existing candidate, although CLI success alone is
not delivery proof.

## Consequences

- Model output cannot choose or alter a recipient.
- A user route cannot silently survive a host API change.
- Revoked/erased routes invalidate pending and leased work before external
  start; a signed prior start remains uncertain rather than being retried.
- Provider and channel substitution become explicit contract tests instead of
  private-adapter patches.
- Stable `v0.21.6` is the current architecture evidence; production `v0.21.3`
  remains untouched until a separately approved upgrade and migration.
