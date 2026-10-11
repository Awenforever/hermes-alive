# ADR-0031: Availability is evidence, not Circadian fiction

Status: accepted for the shadow kernel

## Context

The legacy watcher has two different concepts that both suppress proactive
messages:

- direct operational evidence such as an active Hermes session, an unhealthy
  context queue or a recent effective conversation; and
- Hermes Alive's optional Circadian character model, including sleep phases,
  sleep debt and “forced awake” state.

The live legacy policy currently lets the second category become authoritative
for social quiet behavior. An assistant-side fictional sleep phase is useful as
presentation style, but it is not evidence that the user is unavailable. The
inverse is also unsafe: an “awake” assistant cannot prove that the user welcomes
an interruption.

## Decision

Create a separate user-availability projection with three outcomes:
`blocked`, `explicitly_available`, and `unknown`.

Availability signals are short-lived, authenticated, replayable facts with an
explicit basis:

- `direct_activity` may produce `block` or `unknown`, never `allow`;
- `user_explicit` may produce `allow` or `block` only when causally linked to a
  same-subject inbound user event; and
- `system_policy` requires a separate same-subject policy authority event.

Fresh direct activity blocking takes precedence over an earlier explicit
availability statement. Absence of activity stays unknown. Corrupt or missing
projection state returns unknown. Every assessment reports
`permits_action = false`: availability is one input to interruption policy, not
permission, routing or execution authority.

Circadian state is forbidden from the availability event contract. A
dual-opt-in bridge may mirror the legacy activity guard into the new projection
without affecting the watcher. It stores only structural reason codes and
pseudonymous identities.

## Consequences

- User timing evidence can be replayed and evaluated independently from
  personality or writing style.
- “Hermes is awake” can no longer be treated as proof that the user is
  interruptible in the new kernel.
- “No recent activity” cannot silently become consent.
- The optional Circadian faculty may later survive as presentation rhythm, but
  must lose live authority before the legacy watcher can be retired.
- The current production Circadian gate remains unchanged during shadow
  evaluation; this ADR does not claim that migration is complete.
