# ADR-0026: External start is a durable point of no assumed return

Status: accepted for the shadow kernel

## Context

A lease only proves exclusive preparation. If a process obtains plaintext,
calls a channel, and crashes before recording the result, lease expiry cannot
tell whether the external effect happened. Retrying may duplicate a message;
declaring success invents evidence. A transport idempotency key helps only when
the target capability actually guarantees idempotency and therefore cannot be
the kernel's universal answer.

## Decision

Dispatch has separate `leased`, `started`, `uncertain` and `acknowledged`
states. A worker may release a lease before start. To cross the external
adapter boundary it must call `begin_execution`, which:

1. rechecks the lease, deadline and latest enabled autonomy policy;
2. resolves candidate content inside the kernel;
3. appends an installation-authenticated `dispatch.started` event bound to the
   dispatch, attempt, policy, capability, idempotency key and lease generation;
4. marks the outbox row `started`; and only then
5. returns a one-shot execution grant containing the content and start-event ID.

The event is intentionally written before returning content. A crash or policy
race after that event may conservatively lose an action, but it cannot silently
duplicate one. A started lease that loses its worker or survives gateway
recovery becomes `uncertain` and is never automatically acquired again.

Terminal adapter results must bind the exact start event and generation in
addition to the existing dispatch fields and local authenticator. A valid late
result can close either `started` or `uncertain` work and then enters the normal
outcome projection. Reconstruction recognizes start and result events even if
the operational outbox table was lost.

The v2-to-v3 migration maps old `leased` rows to `uncertain`, clears worker and
token material, and preserves the remaining structural fields. This is a
deliberately conservative upgrade because v2 could not prove whether plaintext
had already crossed the caller boundary.

## Consequences

- Lease expiry before start is safely retryable; expiry after start is not.
- Missing results remain visibly uncertain instead of becoming false failures
  or duplicate attempts.
- A late trustworthy result resolves uncertainty without needing the old lease
  token.
- User pause revokes pending and leased work, but cannot pretend to recall work
  that has already started.
- `begin_execution` is the only API that reveals candidate plaintext to a
  future adapter. No real Hermes adapter is connected yet.
