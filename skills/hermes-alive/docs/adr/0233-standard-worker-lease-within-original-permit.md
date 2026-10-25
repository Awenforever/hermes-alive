# ADR0233 — Standard worker ownership within the original send permit

2026-10-25, Codex. Status: candidate; focused and actual regression pending.

## Observed boundary

The actual r83 native regression completed nine official-model calls, final
source review, authorization and a durable start. It retained the exact share
context before I/O, then failed before the local adapter was entered. The
authorization was issued at13:17:26 UTC, start at13:17:31, reference at13:17:39,
and failure at13:17:45. The worker's default10-second lease had expired during
local validation/context persistence, while the original30-second authorization
window was still open. There was no submission or main turn; this is not a
successful abstention, a model failure or a quality pass.

## Decision

For the ordinary standard-channel path, explicitly request the existing maximum
worker lease from the outbox. Its established acquire operation still computes
lease_until=min(current+MAX_LEASE_TTL, original execute_by). The maximum remains
30seconds; authorization duration and original deadline do not change. Other
callers keep the default10seconds. This aligns worker ownership with the already
authorized execution window, not with slow model inference.

Keep all final launch checks, retention/source checks, one-use start consumption
and unknown-outcome behavior. Never renew a permit or retry a consumed start to
make a late submission succeed. Preparation crossing the original deadline or
revocation must enter the adapter zero times. A genuinely slower preparation
still fails closed; this does not establish unbounded local-work scalability.

## Qualification

Use the actual journal/authorizer/outbox/cycle with a controlled local-preparation
clock:15seconds inside the original window submits once;31seconds or route
revocation submits zero times. Verify one unchanged authorization and lease
clipped to its original deadline, plus existing long-send/cancel/opaque-return
and replay protections. Repeat actual Core source-to-share-to-consecutive-main
behavior; do not turn a synthetic clock into real-source or delivery proof.
