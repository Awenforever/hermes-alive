# ADR-0161 — Durable native cognition host and policy lifetime

Date: 2026-10-16. Status: opt-in actual-Core isolation qualified; no production daemon.

## Integration problem

The previous acquisition probe still manually supplied its operation ID and
lifecycle reader. A real long-lived host cannot mint a model capability before
the durable cycle identity exists, or treat a test boolean as user consent.
The native caller must compose with the existing journal-backed lifetime and
authenticated autonomy policy, without replacing either with another scheduler.

## Decision

`AutonomousHostRuntime.step_bound` opens/reuses the canonical durable cycle under
its existing lock, then invokes a trusted parameter factory with that exact
identity. The factory cannot override subject, operation, execution mode, scan
cursor or cognition configuration. Factory failure leaves the cycle open for
explicit recovery, not a fabricated completion or fresh operation.
Existing `step(dict)` delegates to this path and retains its early validation.

`NativeCognitionHost` composes this factory with `CoreScopedModelAcquirer` and
`HostNativeCaller`. Each cycle gets a fresh operation-bound caller. Its lifecycle
revision derives from the actual authenticated owner-policy event/revision and
host configuration identity; the existing policy verifier also rejects a newer
unreconciled owner command. Disabled policy cannot grant inference authority.
Model/config/scope/credential currentness remains checked by ADR-0160.

The per-cycle capability closes in finally, including exceptions/cancellation.
The wrapper retains any uncertain child and refuses new cycles until its exact
lease is reaped. It rejects overlapping entry and caller-supplied model invocation
or family-resolution callbacks. It adds no platform queue or channel destination,
does not upgrade shadow to execute, and does not claim external delivery.

Acquisition currentness also re-reads the host's credential-name grant before
reading previously permitted values again. A grant-list withdrawal without a
config edit or whole-Alive pause must invalidate the captured capability. This
was missing from ADR-0160's initial implementation; r4 explicitly withdraws the
grant and checks both invalidation and denial of a subsequent secret read.
As with all capability lifetimes, a revoke/regrant ABA that occurs entirely
between observations needs a host-owned lifecycle revision; a current tuple is
not a substitute for that monotonic authority record.

The host still explicitly supplies its profile scope, already-loaded model
configuration, credential-name grant function and model-family resolver. This
composition is not automatic Gateway installation or a complete model-auth
refresh/transport adapter. In particular, a normal single-profile launch with no
Core secret scope must be explicitly scoped by the host; environment fallback is
not used to hide the missing integration.

## Verification scope

Windows `run_autonomous_host_runtime.py` includes cycle-bound parameter factories,
identity override rejection and reuse of the same open cycle after factory failure;
the pre-existing stop/recovery/foreign-owner/execution-mode tests still pass.
`run_native_host_caller.py` also passes. These unit fixtures are not semantic proof.

The actual-Core probe extends ADR-0160 with the durable host and real journal policy:
initial synthetic deliberate silence, a following unchanged-context wake with zero
new model calls inside the reconsideration window, and pause without inference.
The stronger in-flight case pauses via the real authenticated owner event while
the actual native child is held at controlled HTTP, then checks failed synthesis
evidence and absence of a successful host-close event before paused recovery.

The r2 probe's first three sections passed, but its final section expected the
raw NativeWorkerError. Actual synthesis correctly normalized it into
OpportunitySynthesisError with a durable failed receipt. The test expectation,
not the rejection mechanism, is corrected in r3: it checks the wrapper exception,
the failed receipt's NativeWorkerError class, and the still-open durable cycle.
Keep r2 as failed test evidence, not a clean acceptance round.

The complete r3 probe passes all four markers against retained official Core
548e66f in network-none/read-only/capability-free UID1000:10 isolation. Source
snapshot: `/tmp/hermes-alive-installed-RJbQNAiD/cognition-host-20261016-r3`.
Only physical model HTTP is replaced; Core, scopes, native child, canonical
cycle, host lifetime and policy verification are real. No real model calls or
WeChat/email sends occurred; synthetic silence increments no semantic clean-round
count. Production remains untouched. Test containers use `--rm`.
The final r4 source snapshot adds the credential-grant withdrawal case and also
passes all four markers:
`/tmp/hermes-alive-installed-RJbQNAiD/cognition-host-20261016-r4`.

## Unchanged full objective

This closes a composition gap, not the Alive project. Host startup/scheduling and
credential grants still need real installation wiring and qualification. Sustained
real-model initiative, natural expression/silence, layered and external memory,
durable agendas, useful outcome attribution, reflection/learning without drift,
physical forgetting, migration/rollback and production acceptance remain open.
Do not keep expanding route probes instead of exercising those behaviors.
