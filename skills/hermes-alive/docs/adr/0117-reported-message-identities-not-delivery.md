# ADR 0117 — Preserve scoped report identity without inventing delivery history

Date: 2026-10-14

## Finding

Actual pinned upstream `tools.send_message_tool._send_chunks` invokes the sender
for each chunk but returns only the last chunk result. An isolated characterization
through the actual command child calls three synthetic chunk sends, verifies their
order/last flags, and receives only `synthetic-chunk-3`. This is a measured limitation
of the inspected generic helper, not proof that every platform uses that path,
not an audit of production Weixin, and not a wechat-enhance FIFO defect.

Thus a CLI message ID cannot identify all visible bubbles or prove an entire
message was received. Canonical delivered-history capture and feedback attribution
must not be built by promoting this field, nor by guessing the most recent send.

## Change

Typed success-report parsing retains a bounded exact string `message_id` only in
a repr-hidden transient field. Invalid, padded/control-containing, oversized,
non-string and surrogate-containing IDs are unavailable, not normalized. Partial,
error and skipped reports never acquire a successful-message reference.

The authenticated CLI observation may persist an installation-local HMAC of the
exact ID plus platform/profile/chat/thread route. Raw IDs and unknown JSON fields
are not persisted. Same ID on another route has a different reference. Canonical
journal owner/start attribution remains a separate required boundary; the route
hash alone does not authorize an owner or prove delivery/quote association.

These events explicitly retain `external_delivery_proven=False`,
`canonical_quote_target_proven=False`, and the scope
`command_report_not_complete_bubble_inventory`. Their receipt is not accepted by
DeliveredHistoryStore as canonical success. Existing no-ID reports retain their
old structural shape. No new resend, platform FIFO, outcome or learned preference
is created by this change.

## Evidence

Windows report-classification/scoped-identity tests pass, including route
separation, raw-ID non-disclosure and malformed IDs. Linux isolated container
`alive-reported-id-offline-20261014-r1` exits 0 for the same tests, four composed
host-runtime modes, four old host-expression modes and dispatch-cadence regression.
Every host mode also runs the actual three-chunk aggregation characterization.
Successful local-sink command output yields the expected scoped reference; other
modes yield none. Raw `fixture-local-receipt` is absent from canonical journal
JSON. No host observation becomes delivery success or preference evidence.

Network disabled, read-only scratch mount, 1 CPU/2 GiB/256 PIDs. Models/receivers
are synthetic, and the inspected core is the existing pinned export. Dependency
snapshot: ADR-0116 source plus these exact files:

- outbox SHA-256: `ea21deececaa8c4764ab3288a96757324d9e2d5e8520e9fd0f3ab56b8b901a19`
- transport reports SHA-256: `342bae76e446878a2be5d6227836d310ea4c070b72d7d4ff0dcfcc0aff923252`
- host harness SHA-256: `9204c2395976d0016bb4dd1f808349134b626749986615afd8e5227c76dffa07`
- classification test SHA-256: `f6d714dc612851ddba91bf3bb074ac22510b1b2fc18441c194c4b2c50e6c29e2`

Next inspect and qualify actual outbound-event receipt capture, full bubble
inventory and canonical owner/quote binding before connecting native incoming
messages to outcomes and feedback. Do not modify channel queues to obtain it.
Authenticated onboarding, bounded scheduler, model quality, longitudinal utility,
portable lifecycle and production canary remain required. Production unchanged.
