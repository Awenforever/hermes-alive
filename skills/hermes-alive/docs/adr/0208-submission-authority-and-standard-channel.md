# ADR0208 — Submission authority and the standard channel boundary

Date: 2026-10-23 (Asia/Shanghai).
Status: development implementation; final focused qualification passed, broader regression
and installed activation pending.

## Structural defect

ADR0028 correctly separated routes, host capabilities and user authority, but its
eligibility rule required `external_delivered` before any send could begin. A
truthful standard Core adapter reports its own request result, not that the user
received/read the message. Requiring an unavailable stronger receipt prevents
ordinary operation; relabeling the weaker result would fabricate evidence.
ADR0207's actual current-Core lifecycle audit does not remove this mismatch.

## Explicit successor, not a silent relaxation

New v2 route bindings can select an existing ReceiptLevel as their requirement.
They bind the exact host snapshot, locator, subject and prior owner event. That
owner event must explicitly authorize the binding ID, receipt requirement and host
snapshot. The v2 document has a separate authentication namespace; its requirement
is revalidated against the original owner event on recovery. Only channel-send
routes use this successor. Passing no requirement still creates the original v1
contract, which requires external-delivery evidence unchanged.

The host's available public capability must meet the chosen requirement. It is
never promoted to a stronger level. Revocation, owner/capability mismatch, stale
snapshot, missing/erased private locator and malformed evidence remain refusals.
An old route/authorization cannot acquire a lower requirement by reload, migration,
adding a field to a v1 payload or reusing a binding ID. This change grants no
existing production user permission to send; ordinary onboarding must obtain the
new exact grant before enabling its new channel path.

## Standard execution branch

The autonomous cycle can explicitly select the standard host channel boundary;
its existing publisher branch remains unchanged. Standard submission reuses:

- final wording review, source support and exact expression provenance;
- current policy, user route, confirmation/delegation and send-time authorization;
- the existing one-use `dispatch.started` and outbox, not another queue;
- exact-body/media-control/target compilation and a fresh launch-authority check.

A trusted synchronous host resolver receives an immutable exact route and returns
the connected standard adapter AND Core's routing metadata. It must use canonical
receiving-bot/profile routing, not the default bot or an independent lookup policy.
No async resolution gap, standalone fallback, lost workspace metadata, mismatched
thread or host-injected renderer/transport-binding override is permitted. Metadata
marks this as an interim send so it cannot seal an unrelated live final stream.
The body model comes from the exact canonical expression, not ambient config.

The platform's own `send` is called once. Alive neither splits nor retries nor
drains the platform FIFO. Optional Enhance integration remains separately
qualified; the standard branch requires no Enhance installation or private chunk
methods. The host resolver and current-Core assembly are still required work;
this branch alone is not an ordinary installed activation claim.

## Truthful local return evidence

A normal return creates `transport.adapter.observed` over the authenticated start,
generation and route. Persist only a typed reported success/error/unknown category
and an optional keyed opaque-ID reference; no raw body, error, response or ID.
This records neither a complete bubble inventory nor a canonical quote target.
The event cannot acknowledge the outbox or become `delivery.succeeded`, a read
receipt, a human preference or a useful-result learning label.

After a long send, local lease expiry/recovery may already mark the consumed start
uncertain. A same-generation normal return can still be recorded against the
original authenticated route, without claiming delivery or restoring authority.
Exceptions, cancellation, a false/malformed result or observation-write failure
never release the start for an automatic retry. A reopened cycle cannot repeat
the inference or the same external action merely because no delivery was proven.

## Qualification and remaining closure

Tests cover all offered/required receipt levels, exact/missing/foreign user grants,
v1 recovery and downgrade resistance, revocation and private-locator encryption.
The composed real-journal/cycle tests use synthetic models and transport, exercising
normal/false/unknown returns, long-return recovery, cancellation, exceptions,
missing/disconnected adapters, metadata/renderer conflicts, last-moment revocation
and journal failure. Adapter observation cannot be used as a terminal receipt.

The first new test run failed because its frozen fixture clock preceded the
newly created attempt; the start validator correctly refused it. Preserve that
exit1. Fix only the synthetic clock, not the ordering invariant. The successor
focus snapshot passes seven suites and the twelve cases again with actual
v0.22.5 BasePlatformAdapter/SendResult and an in-memory transport. Later added
immutable-resolver-route and authenticated-report-route guards need independent
exact final-tree qualification. Full portable regression is pending at this point.

No real model calls/messages, private chat reads, production edits/restarts, Core
patches, model changes or remote-device changes. No release or platform acceptance.
Next close actual profile/lifecycle-bound resolver assembly, guided authority,
feedback attribution and migration/rollback, then the real consumer matrix and
ten consecutive complete quality rounds. The installed kernel remains shadow.

## Later exact focus qualification

Runtime9aecabe/tree`f003a6fb23948531d33aa08afec10e88b89c2e8c` passes seven managed
Python suites and fourteen composed cases, repeated with actual current-Core
BasePlatformAdapter/SendResult and in-memory transport. This includes the final
immutable-route and authenticated-report-route checks and two further wrong
platform/profile refusals. All focus wrappers have saved terminal exit0, except
the preserved initial clock-fixture failure. Neither an installed Gateway resolver
nor actual platform transport is thereby qualified.

Full portable CI is running on the preceding tree
`1fd5be7841260d6c8ec123c4022a99a3fbf74411`; its actual terminal result remains to be
observed. Do not inherit that result onto the final two stricter guards or claim
the final runtime has full CI, real fleet or production qualification.
