# ADR-0058: Operator-owned process launcher

Status: native Windows isolated process tests passed; production runtime unqualified

## Implementation and evidence

`OperatorCliProcess` launches only its operator-supplied immutable command
prefix/environment and a compiled send argument tuple, without a shell. It
checks profile identity, canonical Hermes home and hashes of explicitly named
artifacts immediately before launch. The executable must have a pin. Case-folded
environment key collisions are rejected to avoid ambiguous Windows selection.
Caller mutation cannot replace the saved command, environment or artifact pins.

Message input is UTF-8 and never an argv argument. Capture uses temporary
regular files rather than pipe reader threads; this avoids pipe deadlocks and
inherited-pipe EOF waits. Input is bounded to 1 MiB; stdout/stderr are monitored
against individual budgets of at most 64 KiB. Normal completion rechecks sizes
and reads only bounded lossless UTF-8 stdout. Stderr is not copied into journal
observations or exceptions. Timeout, output overflow, invalid encoding and
launch/capture uncertainty do not imply a normal CLI observation or no effects.

Actual native Windows subprocess tests pass for multiline Unicode input,
timeout, output overflow, invalid UTF-8, changed profile/arguments/artifact and
immutable binding configuration. The real synthetic recovery authorization now
passes through the bridge and this launcher to a separate synthetic child, then
records a nonterminal observation. Repeated execution does not launch again.

Separately, all six current-upstream public command cases pass through this
launcher to the discovered local platform. The child validates profile and
recompiles with actual host target/media callbacks, checks the parent argument
tuple and invokes the real command handler with the stdin body. This still uses
an isolated command harness, not full `hermes` bootstrap, PM-selected installation
or an external channel. The synthetic authorization chain and actual host
command probe remain separate qualification paths.

## Explicit limits and next steps

- Hash checks bind only named artifacts, not the full dependency/import graph,
  installation provenance or all subsequently loaded code. They are not an OS
  sandbox and do not eliminate path replacement between check and execution.
- Temporary captures contain transient plaintext and are not encrypted memory,
  secure deletion or crash-cleanup guarantees. Before production admission,
  qualify private scratch placement/permissions and retention cleanup.
- Polling enforces an observation threshold, not a hard disk quota: a fast child
  may write more bytes between checks. Production resource isolation must bound
  disk and process-tree effects independently.
- Termination targets the owned child only. It does not prove descendants stopped
  or undo an external effect. Process creation itself is not covered by the
  post-launch timeout. No automatic retry follows any such uncertainty.
- The operator selects prefix, environment, profile and pins; these are not model
  arguments. Actual runtime selection and full-bootstrap qualification remain
  open. No current production launcher is installed or activated.

Next qualify a PM-installed runtime and private resource isolation, combine its
actual command with genuine authorization, then obtain platform receipt and
human/longitudinal usefulness evidence. Do not use these test passes to close
deployment, migration, rollout or the overall Alive acceptance gates.
