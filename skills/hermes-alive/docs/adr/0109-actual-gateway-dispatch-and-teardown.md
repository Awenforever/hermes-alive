# ADR 0109 — Drive the actual dispatcher without confusing it with model delivery

Status: actual runner constructor, _handle_message and stop exercised in
isolation; agent-worker/history/provider and adapter FIFO/delivery unqualified.

## Extend beyond manually composed admission helpers

The new probe constructs the actual GatewayRunner in a disposable standalone
profile rather than fabricating fields on a bare object. It calls the actual
_handle_message from distinct asyncio tasks, with actual session-slot claiming,
running-sentinel checks, slash dispatch, authorization, post-admission dispatch,
post-turn bookkeeping and finalization. The actual Alive plugin is loaded through
its native registration; its opt-in observer writes four structural inputs and
no plaintext or outcome, while a separate metadata fixture tests task handoff.

A subclass replaces ONLY _handle_message_with_agent, the HIGH-LEVEL agent-worker
boundary, with a synthetic async worker. This does NOT replace just the model
HTTP endpoint: worker-side context/media preparation, history loading/flushing,
actual AIAgent behavior and provider routing are not executed or certified.
Calling this the full model/session/delivery chain would be false. The dispatcher
and its slot/control lifecycle are real; the downstream worker is a fixture.

Ordinary authorized input returns the synthetic response. A denied sender and
/help do not enter that worker or generate an admitted Alive/metadata observation.
A second input arriving while the synthetic worker is held does not start another
worker; its own task-private metadata is cleaned. There is no live adapter, so
this checks the real busy branch/sentinel rather than proving queue persistence
or later FIFO drain. Admission is not an observation of every input lane.

Worker failure and cancellation propagate while actual dispatcher finalizers
release the session slot. Their already-admitted inputs remain structural history,
not delivery/user-feedback evidence. The four observed inputs correspond to
normal, held, failed and cancelled worker entries. No user outcome or learning
signal is manufactured, and the actual Alive observer still does not consume the
experimental quote/bot metadata.

## Teardown is necessary, not a cosmetic clean-up

The first attempt shuts down two executor pools manually and then deletes the
temporary profile. Behavioral checks pass, but deletion races background
persistence and fails with Directory not empty; the overall batch exits 1.
This is not a green run. An actual constructed runner owns more state than two
pools, and sleeping or ignoring cleanup errors would hide the ownership defect.

The probe now awaits the actual runner.stop(), checks its shutdown event, and
lets the real shutdown phases drain/quiesce/close storage before temporary
profile removal. No service is launched, no adapters are connected, and no restart
flags are passed. This is normal stop of a local test object, not production
service teardown or upgrade/rollback qualification. Actual physical cleanup now
finishes before the success marker.

## Immutable evidence

Failing snapshot 08898b0fc6f84718a6072d5cf581155a98cd181a, archive SHA256
3a94eb540a7931c049b3afce0bf683a12b6e164aa76920eb2a7204740253f8e6;
alive-full-dispatch-offline-20261014-r1 exits 1 after temporary-directory failure.
Actual-stop snapshot c1b09f8637f970b65839dd3c631e037e6d7b00f7, archive SHA256
98d3070ebeec765d5c5d71d98c4f8f734232c0d21c2b3dc0960ebaf476785e28;
alive-full-dispatch-offline-20261014-r2 exits 0. Adding the actual Alive plugin
gives snapshot 10fd372878feed9f1c62d7759bd004dd22b1a2ba, archive SHA256
60f73e9197db41e4a3403fdf7d3ff30d265f06437c7e9fd85f9fbb492c2b90a9;
alive-full-dispatch-offline-20261014-r3 exits 0.

Final error/cancellation snapshot c9b7e38a9dd17ee60786f2bd103f7626815013db,
archive SHA256 a54bf00523517ce8f9a13834c0b53769e9122061533a8b6c06b970c9c4b4ba82;
alive-full-dispatch-offline-20261014-r4 exits 0 with four actual native Alive
observations, no denied/slash/busy duplicate agent entry, released error/cancel
slots and completed actual stop. The carrier still warns about missing declared
PyYAML/tzdata distributions; this is not installation/dependency qualification.
The network-none/resource-bounded containers use only read-only test scratch and
the pinned ADR-0103 interpreter/core. Audit barriers reject external effects.

No live model calls, real sends, private chats, production/wmw/other-plugin
deployment, restart or model/channel/config change. Real-call totals remain
95 logical / 107 HTTP attempts. Public main/version/README are unchanged.

## Keep the full objective and next critical steps

Qualify delayed/busy/drained inputs with an actual local fixture adapter, the real
agent history/context worker and provider boundary, then connect exact admitted
input and canonical owner/channel delivery history to explicit feedback under
consent. Model review/learning still requires calibrated semantics and useful
longitudinal behavior, not receipt presence. Sustained agenda, layered/external
memory, transitive forgetting, portable lifecycle, migration/rollback and actual
production acceptance remain necessary for the full Alive goal.
