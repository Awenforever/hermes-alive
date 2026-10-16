# ADR-0160 — Current Core scope acquisition and revoked completion

Date: 2026-10-16. Status: qualified in isolated synthetic Core integration;
automatic Gateway scheduling/credential-grant factory and production remain open.

## Why this is needed

An intelligent long-lived kernel must use the owner's actual model capabilities,
not invented aliases, copied process credentials or a competing model registry.
Its learned conclusions also cannot be accepted after the authority under which
they were generated has changed. This connects the model boundary to the real
Hermes scope APIs without granting delivery, tool, memory or learning authority.

## Decision

`CoreScopedModelAcquirer` takes an explicit profile home, current lifecycle-binding
reader, already-loaded host configuration reader, permitted model credential-name
reader and optional identity/keyless grants. It does not discover a profile, read
the complete .env/auth store, install a Core scope or mutate process environment.
The host still owns the grant policy and a monotonic lifecycle generation (ABA
requires a new generation even when config bytes revert).

Acquisition checks Core's `get_hermes_home`, `current_secret_scope_home` and
`current_secret_scope`. An absent or foreign scope fails closed; it never falls
back to an ambient API key. Only the model-related configuration projection and
explicitly permitted secret names are read; unrelated mail/tool/plugin/memory
configuration and secrets are excluded. Core resolves providers, aliases and
fallbacks inside the private child, as established in ADR-0159.

Currentness binds the host's lifecycle record, the actual scoped mapping object,
and a non-exported digest of model settings plus the permitted credential values.
In-place config/credential mutation invalidates the capability; scope replacement
and host lifecycle revocation do too. This does not claim a cryptographic proof
that an embedding host implemented its permission policy correctly. A constant
generation/predicate cannot establish a real consent lifecycle.

`HostNativeCaller` acquires afresh, checks ownership and currentness around secret
reads, and retains bounded child leases. The result must still pass the native
completion binding and a currentness check after the child returns. Revocation
does not unsend an HTTP request already made; it prevents that completion from
becoming an accepted result. Immediate provider cancellation remains a separate
transport/lifetime qualification requirement.

The child environment contains only admitted OS/network/TLS transport fields,
not the caller's credentials, Python path or user profile. Windows worker startup
explicitly sets its private USERPROFILE and removes drive/home aliases. This is
private-process isolation, not a claim that every supported provider's auth
refresh, TLS files, proxy credentials or native transport is already qualified.

## Actual evidence, and its limits

`run_native_host_caller.py` passes on Windows with a replaced child: detached
snapshot, missing/foreign/revoked binding, malformed/duplicate credential names,
projection rejection before secret reads, budget, overlap, retained-child retry
guard, environment filtering and ambiguity rejection. Adjacent protocol,
host-snapshot, completion and client-policy unit suites pass.

`probe_alive_native_host_acquisition.py` runs the actual retained official Core
548e66f APIs, actual native subprocess worker and AIAgent, replacing physical
HTTP only. Core/provider/secret/model/alias/fallback functions are not replaced.
The complete qualified source snapshot is:
`/tmp/hermes-alive-installed-RJbQNAiD/core-acquisition-20261016-r2`.

The container is network-none, read-only, capability-free, resource-limited and
runs as the owner UID with private tmpfs state. It verifies:

- current scoped default and alias select the expected served model;
- synthetic primary403 uses the owner's named backup and correct credential;
- unrelated settings/secrets do not enter the transferable capability;
- foreign and absent scopes reject, without ambient credential fallback;
- mutable settings/credentials and lifecycle generation invalidate old grants;
- a controlled in-flight child is released after host revocation: its valid
  model completion is rejected, its terminal lease/workspace closes;
- the actual canonical Alive shadow cycle uses this acquired caller, produces
  synthetic deliberate silence and replays without a second invocation;
- parent environment bytes remain unchanged.

The first two container launches failed before Python because a private owner700
mount was inaccessible to the chosen UID with DAC capabilities removed. They are
not model failures or successful test rounds. Using the mount owner's UID1000/
GID10 fixes the harness without changing mount permissions or adding privileges.
The r1 probe then passed; r2 adds the in-flight revocation case and passes all
three integration markers. Containers are `--rm`; no live task is assumed.

No real provider calls, channel sends, private user-content reads, production
configuration/Core/plugin changes or Gateway restarts occurred in this work.
Controlled synthetic silence is not natural decision quality or production
acceptance; no semantic clean-round count is incremented.

## Next, toward the full objective

Wire the explicit model-credential grant/current-binding factory into the real
authorized host lifecycle; the current probe supplies a synthetic loaded config,
credential grant list and lifecycle reader. Qualify managed auth/pools, supported
transports and cancellation without exporting unrelated secrets. Then exercise
the acquired caller across sustained public/synthetic longitudinal scenarios:
useful initiative and safe silence, retained/retrieved layered memory, persistent
agendas, evidence-attributed outcomes and bounded reflection/learning. Halo,
physical forgetting, migration/rollback, portable lifecycle and production
acceptance remain required. Do not substitute more routing green checks for those
missing behavioral capabilities.
