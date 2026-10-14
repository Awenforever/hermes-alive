# ADR 0110 — Normalized events are not individual wire messages

Status: real base-adapter debounce/drain and authorized busy-input observation
characterized with local transport and replaced worker. Individual FIFO mode,
real agent history/provider and canonical quoted delivery remain unqualified.

## Actual adapter, not a send-shaped stub

The probe subclasses actual BasePlatformAdapter for four required transport
methods only. connect/disconnect are local state/owned-task operations; send
records a synthetic effect and returns a local-only SendResult. Actual runner
handler wiring, build_source, handle_message, busy admission, text debounce,
background drain, local final-text delivery and normal runner.stop execute.
The high-level agent worker is still replaced as in ADR-0109. A local successful
send is NOT an external delivery or evidence that a human saw the message.

The first worker is held while two separate quoted follow-ups arrive. Under
display.busy_input_mode=queue and inherited busy_text_mode=queue, the actual SDK
combines their text into one normalized event. The final event carries the last
incoming message ID and its quoted-target field is replaced with that incoming
ID, while reply_to_is_own_message remains True from the original fixture input.
The task handoff correctly mirrors those normalized SDK fields; it cannot
therefore certify the original human quote or treat the joined body as a single
wire reply. A structurally complete SDK text snapshot is not physical-origin
proof. Canonical owner/channel delivery matching remains necessary but cannot
alone disambiguate every merged-text path that preserves an earlier quote.

Native Alive payloads now explicitly say
origin_contract=normalized_gateway_event_not_wire_message and
wire_message_count=null. Earlier records without these fields are also unknown,
not implicitly one message. Existing complete-text/truncation flags refer to
the normalized event only. No user outcome/learning is generated.

## Do not repair a high-level worker substitute by blaming the SDK

The initial --busy-text-mode interrupt test (input queue, separate text turns)
fails its strong FIFO assertion and logs orphaned overflow rescue. Replacing
_handle_message_with_agent also removes real _run_agent_drain_pending processing
and overflow promotion; a fake worker is not a model endpoint substitute. Do
not reorder expectations, monkeypatch promotion to fabricate success, or claim
the real Hermes FIFO implementation is broken on this evidence. The failing
individual-turn mode remains an explicit unqualified test; default-mode debounce
characterization does not make that mode green. Actual worker/provider-boundary
qualification is now essential, not an optional extra.

## Find a supported place to observe original busy input

The test uses the actual public set_busy_session_handler API, delegating the
existing gateway handler exactly once and preserving its return value/effects.
After it returns, only input with the SDK's typed bot-admission marker and a
fresh actual scoped authorization check is copied into a synthetic observation
list. Thus two original bodies/IDs/quoted targets can be seen before the base
adapter merges them, without replacing queue/drain/auth behavior. This is a
TEST-ONLY observer, not installed by Alive or permission to persist private text.

The first busy-denial attempt accidentally gave runner and adapter different
group-session key policies: the denied sender reached cold auth, not the shared
busy slot. That run proves only cold denial. The final test configures the actual
adapter extra policy consistently, asserts both senders share the exact adapter
key, and asserts the busy delegate really sees all three follow-ups. Actual busy
auth rejects the unauthorized sender; its body is not copied. No source-payload
shape is accepted in place of the real authorization method.

Next compose a consented, owner/profile-bound busy-wire observer with the existing
cold normalized observer. Distinct observation roles must not double-count
feedback. Lifecycle installation/restoration, fresh authorization and retention
generation, callback failures, scoped profiles, bot/synthetic/control traffic
and original/merged-event provenance require qualification before deployment.

## Evidence anchors and full-goal obligations

Initial tree 8c234b00e819284dc3a7daf5750559b7e1856ccd, archive SHA256
a6d0ec95888a94c5d505133da09eeba867f34e00e4de684481048b52e3b45f45;
alive-adapter-queue-offline-20261014-r1 exits 1 for individual FIFO. The separate
alive-adapter-queue-default-offline-20261014-r1 exits 0 for default bundling.
Intermediate busy-observer tree 3f6fc99d42e8620e3cbb9af28c22e5aa508f2e84, archive
c4ecc3a9460840ed3c84868cdfccd200cedd68df2530cde94e75617698308654 exits 0 but
is cold-denial evidence only. Shared busy-key tree e209e72544a0bc15b822e4236e0157c808577c91,
archive 01468bd12081ed70f851b0ffd901ea8b21781837b83048e97a341f5a6eecb88f
passes actual busy-denial/capture in r3.

Final tree a7aec5fc9ee226a7f34f14c7ede45d156ffad7ac, archive SHA256
b2a0a34e3fef4cce217569e96a2bcfc6ab9621e35bb7f1a94e007121773023b8;
alive-adapter-queue-default-offline-20261014-r4 exits 0 after actual Alive native
observation, default adapter bundling, busy-wire capture, consented-native
regression and prior constructor/full-dispatch/teardown regression. Four wire
arrivals (one denied) produce three authorized original messages, two normalized
worker entries/local replies and two admitted native observations; no outcome.
Windows native-retention regression passes too. This is targeted evidence,
not a fresh full regression run or live transport/production qualification.

A subsequent read-only provenance audit compares 13 relevant NAS export files
with the clean pinned upstream checkout at
3f2abce7f468cf194bb7f9ff9c6a033b075d834c: platforms/base.py, platforms/event.py,
run.py, run_inbound.py, run_busy.py, run_turn.py, run_shutdown.py,
session_identity.py, profile_routing.py, authz_mixin.py, platforms/_shared.py,
hermes_cli/plugins_dispatch.py and agent/secret_scope.py (the first eleven are
under gateway/). Every named file matches SHA256. In particular base.py is
c09968def5166c4ab9f6f08005e65581f54193f5556892f7c49d0a7321f45463;
plugins_dispatch.py is e73aa9e01c3b2dd999fd3a2530e9bc866a3a28f474e6e4c0d5108657271db88d.
This strengthens named-file provenance for the adapter/busy/scoping observations,
not the entire installed import graph or today's latest upstream revision.

Network-none/resource-bounded containers mount only read-only test scratch and
use the pinned ADR-0103 runtime. Declared PyYAML/tzdata installation gaps still
warn. No production/wmw/other-plugin/restart/model/channel/config changes,
private chat reads, real sends or model calls. Real totals stay 95 logical /
107 HTTP. Public main/version/README unchanged. Useful attributed feedback,
calibrated model decisions, sustained agenda, layered/external memory, transitive
forgetting, portable lifecycle and upgrade/rollback plus actual production
acceptance remain the full objective, not replaced by a metadata test.
