# ADR 0155 — Managed native worker lifetime, not cancellation of a thread await

Date: 2026-10-16. Status: implemented single-use child supervisor; isolated proof.

## Component and explicit limits

`alive_kernel.model_process.ManagedModelProcess` owns one host-supplied executable
invocation, explicit cwd/environment and private temporary directory. It is not a
provider resolver, action permit, sandbox, FIFO, process-discovery service or
arbitrary model-selected shell. There is no shell expansion or automatic runtime
discovery. No main plugin entrypoint/production hook is enabled by this component.

A concrete consumer is `probe_alive_managed_native_host.py`: it runs the actual
Core/SDK/plugin-lifecycle/Alive shadow probe inside a supervised Python process,
not a high-level fake conversation worker. Only physical HTTP remains controlled.
No real keys, private history, model calls, sends or production settings are used.

The caller supplies a qualified managed interpreter/entrypoint and scoped
environment; the component neither guesses the parent's profile nor resolves
models. Command arguments must not contain prompts or secrets. Input is bounded
bytes through a private temporary stdin handle, with separately bounded capture
of stdout/stderr. Results hide captured bytes from repr and exceptions are static.
Identical case mirrors in an environment are retained, conflicting values reject;
the original mapping cannot mutate the captured environment.

Regular temporary handles avoid inherited-pipe EOF deadlocks. They contain
transient **unencrypted** bytes, not encrypted memory or secure-erasure proof.
Output size polling detects and stops oversize workers; it is not a hard disk quota
or proof no bytes beyond the threshold were written before observation. A future
native protocol worker must bound its own logs/output and use an admitted private
workspace. Never use production data until that privacy/lifecycle admission exists.

## Start, stop and authoritative observation

One lease admits one spawn only, even after success, timeout, cancellation, output
failure or unknown startup state. The outer durable Alive operation still owns
inference identity/replay; this in-memory lease does not replace the journal.

A retained asynchronous supervisor owns temporary handles through launch, work,
termination and OS wait. Caller timeout sets a stop request, then observes bounded
cleanup; it does not cancel/drop the underlying spawn future. Cancellation and
repeated cancellation likewise do not implicitly start another worker. The loop
remains available rather than blocking on a synchronous native conversation.

Stop requests first terminate, then kill after a grace interval, and wait on the
same owned process handle. A grace timeout is never called termination. If startup
or exit remains unresolved after the observation allowance, return explicit
ModelProcessUncertain while retaining the original supervisor/resources. The host
must reobserve/drain that lease and must not clean its workspace or retry it.
Status/PID are diagnostic; no later process is found or killed by PID/argv guessing.

The supervisor proves only **the direct owned child is terminal**. Result explicitly
sets process_tree_terminal_proven=false. Arbitrary descendants, host-parent crash,
event-loop destruction and cross-restart OS lease adoption are not solved here.
The host must drain live leases before shutting its event loop/profile. Production
needs a constrained native entrypoint plus qualified parent-death/process-tree
handling for its actual platform, not just this helper. Stopping a client also
does not prove an already received provider request was not computed or billed.

## Actual OS and Core evidence

`run_model_process.py` uses real subprocess handles on the actual current OS. It
exercises stdin echo/private result repr, explicit nonzero exit, output overrun,
timeout, ignored termination followed by kill on POSIX, cancellation/repeated
cancellation, invalid input and failed launch. A delayed-spawn fixture holds the
same real launch behind an event: an observation deadline returns uncertain, files
remain open, another run refuses, then releasing that same gate creates one child
which is stopped/waited and its capture handles close. The delay is controlled;
it is not evidence an OS-level spawn hang itself was reproduced.

The real-Core consumer checks successful native constructor/prompt, retained
memory/agenda/discovery/feedback shadow/replay/withdrawal, and scoped completion
markers. It then holds the first synthetic provider request in a second actual
Core process, observes its ready PID matches the owned handle, cancels repeatedly,
waits for nonzero child exit and refuses partial stdout as a completed model reply.
This is client/worker cancellation, not live-provider cancellation semantics.
Both child temporary homes/cache/Profile paths are placed under the parent-owned
private workspace via child-only TMPDIR/TEMP/TMP bindings, not left in the global
system temp directory when a child is killed. Parent cleanup occurs after both
owned children are observed terminal. Probe-owned Alive shared-runtime paths also
override inherited shared-dir settings before kernel import. A disposable Docker
tmpfs is not used to disguise this per-worker workspace responsibility.
An expanded rerun exposed a readiness-file publication race: file existence was
visible before the PID writer flushed its buffer. Publish the complete ready record
by atomic rename, not by treating an empty file as readiness or retrying an arbitrary
parse. The parent probe also explicitly cancels/drains in finally on readiness or
assertion failure, before its private workspace context ends. The failed run is not
counted as a pass or attributed to the model.

That trusted child probe installs Python audit denial of descendant creation
before importing Core. The first attempts failed an incorrect *zero spawn attempts*
assertion: actual Core env_probe wanted another Python-version process and the SDK
platform probe wanted a processor command. Both attempts were blocked before
creation, and Core otherwise completed. Do not allow subprocesses to make this
assertion green. The revised test explicitly challenges denial with a canary,
retains the blocked metadata attempts and checks the shadow loop still works.
Python audit denial is a trusted-runtime policy, **not an OS security sandbox** or
generic process-tree attestation. CLI/ACP providers requiring child processes are
not qualified by this test and must not silently lose their functionality.

Success markers distinguish the layers:

```text
HERMES_ALIVE_MODEL_PROCESS_OK
HERMES_ALIVE_NATIVE_CONSTRUCTOR_PROMPT_BOUNDARY_OK
HERMES_ALIVE_NATIVE_SHADOW_SOURCE_BOUNDARY_OK
HERMES_ALIVE_NATIVE_SCOPED_COMPLETION_OK
HERMES_ALIVE_MANAGED_NATIVE_HOST_OK
HERMES_ALIVE_MANAGED_NATIVE_CANCEL_OK
```

The process suite passes on native Windows. Actual Core is exercised only in the
retained isolated Linux environment, not a new Windows Hermes installation. A
complete managed-native probe has three fake provider replies plus one held fake
request, zero actual model calls and zero channel sends. Real usage totals remain
290 logical/304 observed async HTTP starts. Controlled replies prove composition
and lifecycle, not model quality or independence. Synthetic subprocesses/containers
are terminal before their test workspaces are cleaned.

## Next integration and original objective

Build an admitted native worker protocol with exact parent operation/context
binding, inherited Hermes primary/custom/fallback routing and consented identity,
bounded private output, scoped completion evidence and stop/restart ownership.
Do not transfer an entire production Profile or foreground session into a worker.
Preserve current-source/consent checks around the await and failed-inference replay
rules; do not add automatic retries or adopt a partial result after cancellation.

Then use actual configured models on sustained shadow scenarios before choosing a
replacement for the current intermediate-plan architecture. Useful expression,
safe silence, lasting agenda, attributable feedback/reflection learning, external
memory/Halo, complete erasure, migration/rollback, portable installation/upgrade
and production acceptance remain required. This stage neither enables production
nor completes any of those broader gates. Enhance, Core, model settings and
network remain untouched; FIFO/Token stay Qoder-owned. No main release/deploy.
