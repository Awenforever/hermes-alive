# ADR-0159 — Native host snapshot resolution and credential admission

Date: 2026-10-16. Status: explicit private-worker integration qualified in isolation;
automatic live host capture and production activation remain incomplete.

## Decision in the full objective

The native worker can now accept either an already-resolved capability or an
explicit model-only host snapshot. The trusted owner supplies configuration,
permitted secrets, selected model and optional unauthenticated endpoint grants.
It must still validate subject/operation/current consent before and after the
invocation. Alive does not discover a profile, copy a foreground session or
change the live Gateway's environment/model settings.

Core resolves the snapshot inside the already-owned private process. This moves
real default/alias/provider/fallback parsing and credential selection to Hermes,
instead of asking an Alive caller to implement a competing model registry.
This integration is necessary for useful native cognition, not a substitute for
that cognition or the retained-memory/agenda/outcome/reflection/Halo objectives.

## Capability lifetime

The finite snapshot contains only model/provider/alias/fallback/routing config,
model reasoning/tier settings and explicit secret mapping. No plugin/hook/tool,
mail, foreground session or memory configuration may be included. Config is
detached before local forced lifecycle settings are added. The snapshot is
bounded and included in the existing owner/operation/context request checksum.
It grants no delivery/action/consent authority.

Text-only request/budget restrictions cover the entire projected model graph,
including unused/later fallbacks and per-model extra_body/request_overrides.
Core can re-read those settings after the primary fails, so checking only the
initial selected runtime would leave an authority/budget bypass. The shared
override validator applies to both resolved envelopes and projected configs;
negative tests reject a fallback tools declaration and nested token override
before worker creation. This is an API capability boundary, not mail-content
classification or a semantic-quality heuristic.

Core secret scope is bound to the private profile with multiplex isolation before
resolution and kept alive through native agent close, including fallback/client
rebuilds. Core's frozen runtime config covers resolution and the conversation;
the private on-disk model projection also preserves per-model routing/reasoning
and provider header/body policies for Core readers. ExitStack resets these
bindings on success and exception. No live process environment is rewritten.

The actual Core startup route, runtime-with-fallback, fallback-chain/key and
effective-provider helpers are used. An explicitly selected model wins over a
provider's default. Resolution-time fallback changes the active model and the
remaining chain, rather than retrying earlier entries forever. Explicit empty
fallback remains empty. Custom request_overrides/capabilities and Core-resolved
reasoning/tier are carried to AIAgent; Core still owns its fallback rebinding.

A credential pool created by Core **inside the private worker** stays a native
in-process object. It is removed only for JSON route validation and then passed
to AIAgent; it is never serialized from the parent or stringified. This does not
prove migration of a real auth store, OAuth refresh or arbitrary callable keys.
Callable primary credentials, command/CLI routes, external CA files and ADR0158's
unqualified transport/anonymous-header combinations still reject visibly.

Core pads missing custom credentials with `no-key-required`. That SDK padding is
not owner authorization. A host snapshot must explicitly list a matching
`unauthenticated_endpoints` destination before that placeholder is admitted.
Otherwise fail before model HTTP, even when an ambient key exists. Unit coverage
also preserves the explicit keyless grant path; actual keyless servers remain
unqualified. Do not infer permission from localhost, provider name or a timeout.

Worker errors now expose only a fixed structural phase and exception class;
there are no raw provider messages, prompts, headers, secrets or tracebacks in
the worker envelope. Existing exact completion binding/no-authority remains.

## Evidence and failed assumptions

Windows host-snapshot/protocol/completion tests pass. The complete actual Core
archive548e66f and retained managed dependencies run in network-none, read-only,
resource-limited owned containers with private temporary profiles. HTTP is
controlled only at physical httpx send; resolver/config/auth/alias/AIAgent/native
observer/fallback functions are not replaced. This is not a fresh install or a
real endpoint availability test. The last complete snapshot is
`/tmp/hermes-alive-installed-RJbQNAiD/host-snapshot-20261016-r9`.

Actual default, alias and403 -> named backup succeed with the correct scoped
keys/header policies despite conflicting ambient keys. Custom extra_body reaches
the primary request. Missing owner credentials and empty fallback reject before
model HTTP. OpenRouter controlled wire carries per-model `only` overriding flat
pins and `data_collection=deny`; unrelated custom endpoint headers are absent.
The same host-snapshot path runs the canonical Alive shadow cycle, and a replay
does not invoke a second worker. Output is synthetic deliberate silence, not
proof of intelligent content or ten clean longitudinal real-model cycles.

Failures remain evidence:

- r1 left client_policy in AIAgent kwargs after snapshot resolution: TypeError.
  Policy is now applied in private config and removed before constructor call.
- r3/r4 missing credentials became Core's SDK placeholder, then failed controlled
  HTTP assertions until the owned timeout. The absent runtime key_env metadata
  made a first narrow guard ineffective. Explicit unauthenticated capability
  admission now rejects this before HTTP; no ambient key or fallback is invented.
- r5/r6 encountered the previous cross-process pool prohibition for Core's own
  locally constructed pool. r7 preserves that pool inside the private process.
- r7/r8 then exposed an invalid test assertion: every common-header request was
  required to carry the synthetic custom endpoint header, including OpenRouter.
  Recorded wire already had correct model pins/privacy and no custom header.
  r9 scopes the header assertion to its exact endpoints and explicitly forbids
  leaking it to OpenRouter. This changes the test expectation, not Core policy.
  The older diagnostic `route=false` on OpenRouter means the synthetic custom
  header is absent as required; it is not a failed privacy-field check.

No real model calls or WeChat/email sends, no production/source Core edits and
no changes to production model settings occurred during these experiments.

## Still required

Build the host-owned capture/factory that selects necessary capabilities from
the actual current owner without copying an entire .env/private profile. Its
environment must be deliberately minimal, not an ambient credential dump. Bind
profile/model/config revision and consent lifecycle, and qualify config changes
during calls. Test additional transports, TLS/CA materialization, keyless local
models, real auth refresh/pools, and all fallback policy changes. Existing
unqualified cases stay explicit, not erased to pass a text request.

Then use the correctly inherited native caller for sustained real synthetic/
public autonomous scenarios: recover candidates, make useful choices, express
natural messages or stay silent, retain/retrieve memory and agendas, attribute
outcomes, reflect and learn without drift. Prior semantic failures remain open.
Halo, actual forgetting, installation/upgrade/migration/rollback and production
acceptance remain part of the unchanged living goal.
