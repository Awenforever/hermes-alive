# ADR 0118 — Stock Weixin results lose partial-effect evidence

Date: 2026-10-14

## Actual host evidence

`run_host_weixin_send_receipt_probe.py` constructs the actual pinned stock
WeixinAdapter and executes its actual formatting, extraction, splitting and
send loop. Only `_send_text_chunk` network IO is replaced by a controlled local
acknowledgement/error/cancellation seam. No login or real send occurs.

The actual method produces seven chunks and returns only the last locally
generated client ID. A failure on chunk two can follow an accepted chunk one,
yet returns a false SendResult with no message ID. Failure on chunk one has the
same public error fields as failure after that partial effect. Cancellation on
chunk two propagates CancelledError after a prior accepted chunk; it does not
become a successful result. This strengthens ADR-0117's generic helper finding.

These are local controlled acknowledgement effects, NOT measured Weixin server
delivery or user receipt. The production wechat-enhance queue is not installed
or audited by this experiment, and no defect in that plugin is inferred.

## Consequences for the runtime

- A false adapter/CLI result must not imply zero external effects or safe resend.
- A locally generated final client ID is not a complete bubble inventory or
  verified quote target. Do not guess omitted IDs or associate the latest action.
- Capture must distinguish an adapter invocation, individual confirmed protocol
  acknowledgements, whole-action completion and user feedback. Missing evidence
  stays unresolved, not a delivery success and not a negative user preference.
- The inspected `gateway_platform_event` SDK surface lists event-specific
  reactions/edits/deletes/thread events, not a universal outbound-ack contract.
  Do not register an inert imagined send hook or use agent:end as post-delivery.
- Next qualify an owner-scoped observer of the actual send boundary, preserving
  original result/exception/cancellation and restoration/unload ownership. It
  must not enqueue, reorder, refresh tokens or retry; those platform operations
  remain host/wechat-enhance responsibilities. Shared/queued task provenance and
  unsupported adapters must stay explicit until tested.

## Qualification

Linux final probe passes, command exit 0, with source-file SHA-256
`bd0b327903db3d1d4b2d53364346d04d01c4474436f4f36b4e9eb02412863c1d`.
Inspected actual Weixin source matches the clean pinned upstream reference file:
SHA-256 `74a735ef94d8a21a47ef42cd0cd237de49c0968ec248c7bb595564d3139fe764`.
This is named-file provenance, not full newest-core qualification.

The previous initial run failed before test execution because an audit callback
was incorrectly called rather than registered. Fixed via `sys.addaudithook`;
no product behavior was altered to obtain a passing result.

Container uses network none, 1 CPU/2 GiB/256 PIDs, read-only scratch mounts and
explicit test ownership label, and `--rm`. Its absence is checked before/after;
stdout/exit status and source digest are retained outside the disposable layer.
No duplicate source tree or stopped container remains from this probe.

Old test trees/containers were safely archived and cleaned at the user's request.
Keep one current source snapshot and reusable managed interpreter/core export;
restore old evidence selectively, not entire retry trees. Future disposable tests
must save necessary evidence and remove confirmed-terminal containers, never
global-prune or force-stop production. The active kernel goal remains unfinished:
receipt capture, attributed feedback, authenticated opt-in scheduling, actual
model quality, longitudinal usefulness and portable/production acceptance remain.
