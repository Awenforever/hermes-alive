# ADR 0131 — Durable host cycle identity and cooperative lifetime

Date: 2026-10-15

## Implementation

`AutonomousHostRuntime` is an explicitly invoked, bounded lifetime around the
composed cycle runtime, not a gateway hook or installed background service.
Canonical owner/lane/configuration/mode-scoped journal events own cycle identity
and the next reconciliation scan cursor. An unfinished cycle reopens as the same
operation after restart; a changed configuration or shadow-to-live mode refuses
to reuse it. Only a qualified result closes the cycle and allows another identity.
Closing the control cycle never claims remote delivery or grants permission.

Open/close allocation and canonical replay occur under the journal writer lock.
Owner/lane participate in authenticated identity, not just unsigned envelope
headers. Completion links back to the actual authenticated open operation.
Copied signed payloads with another owner's rewritten headers are refused.
One host instance serializes step calls; this is not cross-process execution fencing.

`run` requires an explicit maximum cycle count and cadence, checks the stop event
before starting work and cooperatively cancels/joins its active cycle and stop
waiter on shutdown or external task cancellation. A failed cycle exits with an
explicit failure status and retains its open identity rather than silently
allocating a replacement provider operation. A callback that ignores cancellation
or blocking synchronous IO is not proven bounded by this design. Stop is a host
lifetime signal, not a claim that already accepted FIFO messages were recalled.

The host supplies a non-secret configuration identity, real configured-model/
channel callbacks and existing authority. It does not create credentials, grants,
personal defaults or a competing Weixin queue. Actual model/transport recovery
remains with the underlying runtime and its existing incomplete-operation gates.

## Evidence

Windows and Linux host-state tests use a fake cycle driver to check failed/open
identity preservation, reopen, next identity only after closure, explicit cycle
budget, independent owner identity, cooperative stop during active work, external
cancellation cleanup, pre-stopped/no work, changed configuration refusal,
unfinished shadow-to-live refusal and foreign signed payload cloning refusal.
These test state/lifetime machinery, not provider intelligence or sending.

The separate composed cycle test now also runs two host-driven shadow/silence
cycles through the actual discovery/planning/expression/control modules, with
synthetic model replies. Windows and Linux actual stock Weixin constructor/send
with only physical IO replaced pass this addition alongside the prior once-only
queued submission, replay, shadow, silence and pause cases. No further action
attempt is created by those two shadow cycles.

The initial standalone Linux host test failed before execution because the shared
overlay runner expected a producer source mount not supplied in that invocation.
The corrected read-only mount invocation exits 0; the initial run is not a pass.
Final containers use --rm, network none plus audit guard, bounded resources and
the retained base snapshot/current-file overlays. No full new clone/snapshot,
labelled residual container, real model call, actual channel send, private-history
read or production configuration/deploy/restart occurred.

## Outstanding whole-system qualification

There is no public lifecycle registration, process-level ownership fence, paired
state/config migration, scan retirement, long-history/performance qualification
or installed-device proof yet. Automatic multi-cycle execution must qualify
unresolved-intent/novelty suppression and cost controls before activation; a
closed submitted cycle is not evidence that its content may safely be sent again
under a new cycle identity. Failed/incomplete model work still needs explicit
bounded recovery rather than provider retries inferred from a restart.

Inspection also found that prepared generated text currently reaches the publisher
without the retained renderer's actual-model metadata. Model footers therefore
can fall back to a system/other-turn label. Carry authenticated renderer provenance
at the prepared send boundary and verify every native chunk; never substitute the
configured main model, reviewer model or a hardcoded model name. This remains a
pre-activation gap, not a production deployment regression from this prototype.

Real-model grounding, useful diverse initiative, sustained agenda, memory
correction/forgetting, canonical attributed feedback/reflection and longitudinal
benefit remain unproven by these synthetic replies. Portable install/upgrade,
authorization continuity, migration/rollback and real production acceptance stay
in scope. Enhance's independent final release/acceptance remains after Alive.
Do not mark the goal complete or enable production based on this host prototype.
