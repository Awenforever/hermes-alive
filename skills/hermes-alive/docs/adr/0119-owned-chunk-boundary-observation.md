# ADR 0119 — Owned chunk observation without transport ownership

Date: 2026-10-14

## Research implementation

Add opt-in `OwnedChunkObserver` around an explicitly operator-qualified adapter
chunk seam. It delegates once to the original method with identical arguments
and preserves its return, exception and cancellation. It neither sends on its
own, retries, changes tokens nor owns FIFO. No runtime hook registers it yet.

Capture requires the exact owning asyncio task and operator chat route. Other
tasks/rooms are not captured. Same-chat work on another task marks coverage
uncertain; it is never associated by recency or inherited task context. Child
queue task provenance remains unqualified, so this is not yet a production
wechat-enhance compatibility claim.

Only normal None returns at the qualified seam yield bounded typed observations.
Unexpected return shape/invalid ID/hash failure makes observation unavailable
without replacing a completed original result. Capacity overflow stays explicit.
The stored reference is an installation-local HMAC of owner, exact route and
client ID; no message body, context token, raw client ID or exception text is
retained. Public snapshots are immutable tuples. These observations are not
canonical delivery receipts, user receipt, quote targets or permission.

Exit restores the prior instance/class method only while this observer owns the
slot. A later plugin's replacement is never clobbered. Observation stops on exit;
a dormant coroutine retaining the retired wrapper still delegates normally.
The observer drops adapter/task/wrapper references on exit. Reuse/double install
and absent explicit operator qualification are refused.

## Evidence

Windows `run_owned_chunk_observation.py` passes own-task capture, foreign task/chat
exclusion, unchanged original error/cancellation, dormant invocation, bounded
capacity, observation failure, owner-separated references and restoration conflict.

Linux actual stock Weixin constructor/send loop, with only network chunk IO
replaced, passes with observation enabled: seven normal returns recorded on full
completion; one retained normal return before mid-send failure/cancellation;
none before first-chunk failure. Original method restoration and unchanged public
result/exception behavior are asserted in each case. No body/token is recorded
by the observer. The pipeline does not publish canonical delivery/history from
these diagnostic findings.

Final input hashes:

- observer: `97c1d712523327e3beb8a48a063646311e2b0a42b7f4e10e7099ea6f2b2dec35`
- host probe: `5e278316f6d61d0f2e318c791a088b7f1eda88156e5659815f358028a1cab41f`
- Windows contract test: `00337300528cfc52264d69cdb9e4eeebd00e0a9e4f51daea0ad7a4a210fe41aa`

Linux uses the preserved current test source for unchanged dependencies and an
explicit read-only observer module overlay; no new retry source tree. Container
`alive-chunk-observer-current` exits 0 with network none, bounded resources and
`--rm`; absence after completion is checked. Logs/digests live outside its layer.
This is not full installed-package/Windows host/shared queue/real delivery proof.
Production remains unchanged, and no real model or channel call occurred.

## Next

Qualify concurrent ownership, queue-task handoff and unload before using this
on shared live adapters. Connect authenticated retained attempt-bound receipt
publication with consented historical text and trustworthy quote feedback.
Preserve unsupported/ambiguous states and existing transport ownership. Continue
authenticated controls, scheduling, actual model quality, longitudinal usefulness,
portable lifecycle and production acceptance; the Alive goal is not complete.
