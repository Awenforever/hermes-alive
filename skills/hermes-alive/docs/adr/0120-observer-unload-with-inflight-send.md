# ADR 0120 — Unload is a publication boundary, not send cancellation

Date: 2026-10-14

## Reproduced defect

ADR-0119's observer checked owning-task scope before awaiting original chunk IO.
If another task unloaded it while IO was suspended, the old scoped boolean still
allowed a late return to append a record. The new barrier test reproduced
`late return published after unload`. Double close could also access a cleared
adapter reference. These are observer-prototype defects, not Weixin FIFO defects.

## Fix

Publication and error/cancellation counters check active observation again after
the await. Closing is idempotent, ends capture immediately and records
`closed_with_pending_calls` when own-task IO remains outstanding. Inflight counts
are released in finally, including original failures/cancellation. The original
send itself is never cancelled, retried or changed by unloading observation.

Normal return, original exception and original cancellation are propagated
unchanged even when they occur after close. A late result cannot grow the closed
snapshot. The pending-close marker stays true after IO finishes: it denotes lost
coverage, not completed delivery. A context-finally may close a second time safely.
Other owners' method replacements are still not clobbered. Existing retired
wrapper calls continue to delegate without capture.

## Evidence

Windows tests first fail on the unfixed late-publication invariant, then pass
the fixed observer. Tests cover unloading suspended return/error/cancellation,
zero post-close records/counters, inflight completion and repeated close. A
second observer cannot replace an active owner. Existing owner/task/chat scoping,
capacity, metadata failure, reference privacy and method-restoration cases pass.

Linux explicit module overlay of the same current code passes the same unit
suite and the actual stock Weixin constructor/send-loop regression with synthetic
chunk IO. Seven complete normal returns remain observed; one before partial
failure/cancellation remains observed, with original results unchanged.
This is not full installed-package qualification or a shared FIFO-worker handoff.

Input hashes:

- observer: `c6f4b6d2571198fea5b85766dba38e61c3dc4ab95e2fc32c1a1edb7d3895c6b3`
- unit test: `3c625019a3ceace2e34b011e9b772796b901debbdd13cf04cebb83b1a240984c`
- host probe unchanged from ADR-0119:
  `5e278316f6d61d0f2e318c791a088b7f1eda88156e5659815f358028a1cab41f`

An initial Linux launcher attempt failed before tests due to nested shell quoting
in an inline Python command. A fixed reusable file runner aliases the explicit
read-only current module into the retained package namespace and runs the tests;
no product code or invariant was weakened. Final process exits 0. Network is
disabled, resources bounded and disposable container auto-removed; no additional
source tree is created. No real models, private chats or external sends were used.

## Remaining integration

Do not claim actual shared/queued task ownership or production plugin compatibility
from these barriers. Next connect bounded attempt-scoped publication and verify
queue-task provenance without owning/rewriting the channel queue. Then qualify
consented historical text, quote attribution and feedback, user opt-in controls,
scheduler activation, real model quality, useful longitudinal behavior and
portable/production lifecycle. The full Alive goal remains active; production and
wechat-enhance have not changed.
