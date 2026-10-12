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
