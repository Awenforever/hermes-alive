# ADR 0128 — Authorized host-owned withdrawal of pending submissions

Date: 2026-10-14

## Implementation and responsibility

Enhance development commit `6b9b41f` adds a trusted-host withdrawal interface.
Alive does not delete or reorder its FIFO. The host persists an account/chat/
opaque-binding deny before awaiting its physical-send lock, removes matching
pending rows transactionally and publishes the local `withdrawn` phase. The drain
checks the deny between chunks; later submissions under that same binding are
suppressed. Unrelated bindings and unbound messages retain their queue position.

This is not remote recall. A physical call already in flight may finish and is
recorded as acknowledged, not falsely withdrawn. A drain can perform cleanup
before the withdrawal caller obtains the lock, so that caller's removed_count
is not a total count for the intent. Durable denies persist across reopen,
never auto-evict and refuse a new request at the 10,000-entry bound. Their
controlled retention/erasure and failure handling are not yet fully qualified.

`TransportPublisherBridge.withdraw_paused` requires the current explicit owner
pause, checks the canonical self-authorized signed policy event and rejects
newer authenticated owner commands absent current-state reconciliation. A forged
cache flag or a stale genuine pause after resume cannot authorize withdrawal.
Qualification includes exact binding/route/account/epoch and the cancellation
method's source digest. Signed request/report events preserve provenance and
deny delivery/recall/inventory proof. The caller still supplies a trusted current
publisher; no inbound command handler or background subscription is installed.

A previous report is historical evidence, not proof that a restored host database
still has its deny. An authorized replay reasserts the idempotent host request
before returning the existing canonical report. This repairs simulated deny loss
when invoked; it is not automatic full restore qualification or a total-effect
report. Lost-result requests can reassert the deny without a second send.

## Evidence

Windows fake transport and Linux actual stock Weixin constructor/send with only
physical IO replaced exercise the actual enhance code: interleaved A/B/A FIFO
withdraws only A, persistent deny after reopen, new A suppression, route/account
isolation, repeat request and an asynchronous physical-IO barrier. At that barrier,
the first A is already in flight and finishes; later A is suppressed and unrelated
B continues in FIFO order. No promise is made to unsend the first A.

The real kernel-start/publisher integration tests also pass on Windows and Linux:
enabled policy refuses, forged pause cache refuses, explicit signed owner pause
withdraws, replay adds no duplicate journal report, simulated host deny loss is
reasserted, and a genuine old pause cannot be replayed after a later owner resume.
Queued/withdrawn observations are retained but do not become delivery outcomes or
negative feedback. Existing enhance FIFO/model/context-token/retry and producer
tests pass after the additive schema/interface changes.

Linux final processes exit 0 with network none plus audit guard, bounded resources,
read-only current-file overlays and --rm. No full clone/source snapshot, real model
call, actual channel send, private chat or production update/restart occurred.
Enhance remains on its independent development branch. The first push encountered
a terminal TLS failure; a read-only remote check confirmed it had not advanced,
and the safe same-branch retry succeeded without network configuration changes.

## Remaining gates

This does not establish a fully atomic pause command across threads/processes,
task cancellation while waiting for the IO lock, database failure/capacity,
deadline/grant expiry at deferred send time, source upgrades or coordinated
restore. Existing foreign-process access and arbitrary tombstone deletion are
not solved by the in-process lock. A withdrawn user intent must never be revived
by guessed absence of effects. Production control admission must reconcile all
affected bindings rather than only this explicitly invoked one.

Next qualify bounded control/subscriber lifetime and these failure/migration
boundaries, then useful autonomous scheduling, canonical attributed feedback and
longitudinal real-model utility. Portable fresh install/upgrade/rollback and
production acceptance remain required. Enhance final release/acceptance stays
after Alive; no activation follows from these tests.
