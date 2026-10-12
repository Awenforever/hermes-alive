# ADR-0054: Public CLI is a transport candidate, not delivery proof

Status: accepted for source characterization; execution bridge not qualified

## Evidence and correction

ADR-0028 correctly rejects treating `PluginContext.inject_message(True)` as a
completed send. Its implication that a new upstream public API is necessarily
required before investigating any send bridge was too broad.

Official source at `3f2abce7f468cf194bb7f9ff9c6a033b075d834c` exposes
`PluginContext.dispatch_tool`, but the send helper explicitly states that
`send_message` is intentionally not registered as an agent-callable tool.
Method existence is not proof of a registered handler. We must not register
a fake handler, access the private gateway adapter map, or claim an actual
registry invocation has been tested from source inspection alone.

There is a supported `hermes send` CLI. This is a legitimate transport
candidate, not grounds to postpone all host integration until upstream adds
another plugin method. It still needs profile isolation, explicit route
binding, authorization and ambiguous-result handling before execution.

Primary source:
- https://github.com/NousResearch/hermes-agent/blob/3f2abce7f468cf194bb7f9ff9c6a033b075d834c/hermes_cli/plugins.py
- https://github.com/NousResearch/hermes-agent/blob/3f2abce7f468cf194bb7f9ff9c6a033b075d834c/tools/send_message_tool.py
- https://github.com/NousResearch/hermes-agent/blob/3f2abce7f468cf194bb7f9ff9c6a033b075d834c/hermes_cli/send_cmd.py

## Result semantics

The actual upstream CLI result emitter is exercised without invoking sends.
Duplicate suppression has exit status zero; a partial effect can have failure
status; a truthy non-boolean success value also has zero status. None proves
that a new complete message reached the external recipient.

These are injected payload characterization cases against a source snapshot,
not end-to-end transport results. The test prints source digests and explicitly
marks every case as not proving external delivery. No credentials, actual
routes, gateway launch, model call or external send are needed.

The executable characterization used the preserved local snapshot
`f925b01791fe052e7d55dc975750c0bd985aff91`; all seven cases passed. The newer
commit above was inspected through official raw source, not installed or
executed. These are separate evidence scopes, not a latest-runtime claim.

## Next qualification

1. Probe the actual loaded public registry in a disposable profile without
   adding a send handler or importing production secrets.
2. Exercise the public CLI against a controlled platform test endpoint, using
   a separate approved route. Preserve explicit JSON and partial/skipped states.
3. Define what each platform acknowledgement actually proves. Do not infer
   human attention, benefit, completion or reading from a transport response.
4. Connect only a qualified interface to the authorized outbox. Interrupted
   or partial external attempts remain uncertain; do not blindly resend.

Production remains on the legacy implementation. No live bridge is activated
by these source tests. Do not weaken the authorization or receipt gates merely
to make an interface test pass.

## Actual SDK probe, 2026-10-12

`run_host_transport_registry_probe.py` now invokes the real public
`PluginContext.dispatch_tool` against the real registry in the preserved
`f925b01` snapshot. Before and after importing the official send helper,
`send_message` is absent and dispatch returns `Unknown tool: send_message`.
No tool handler is registered or patched by the probe.

The same child exercises the public `register_send_subparser` and `cmd_send`
path with `send --list --json`; the credential-free profile reports no
platforms and exits successfully. This establishes command-parser/handler
availability, not delivery capability or full CLI-bootstrap readiness.
The CLI bootstrap is deliberately not invoked: it includes interrupted-pull
recovery that can mutate the source checkout.

The child receives an environment allowlist rather than inherited provider,
proxy or production profile settings. It uses a disposable home, disables user
site packages and disallows socket construction and process launch using audit
hooks. Negative checks prove both barriers refuse before OS effects. Source
digests identify the actual SDK, registry, helper and CLI files exercised.
The only extra local dependency was `ruamel.yaml` in the test-only venv;
no production dependency or configuration was changed.

Scope is a fresh manager and actual helper import, not a fully discovered
gateway/plugin deployment. A third-party profile could register a same-named
tool; that would be a different capability requiring explicit qualification.
Both this SDK probe and the seven CLI-emitter cases were subsequently repeated
against a separately materialized `3f2abce` worktree and passed. The four
exercised source digests are identical across these two revisions. The first
new-worktree attempt lacked `hermes_cli`/`tools` because it inherited a sparse
gateway-only checkout; expanding only the new worktree fixed the test input,
not the Hermes API. The old snapshot remained at `f925b01` with its original
sparse configuration. No upstream source files were edited.

This qualifies the bounded current-upstream source/SDK path on native Windows,
not a complete PM-installed Hermes, full bootstrap or gateway/plugin discovery.
Controlled platform transport, profile credentials and live receipt semantics
remain unqualified.
