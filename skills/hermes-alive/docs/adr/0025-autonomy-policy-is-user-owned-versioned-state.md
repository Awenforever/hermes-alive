# ADR-0025: Autonomy policy is user-owned, versioned state

Status: accepted for the shadow kernel

## Context

A `PolicyContext` supplied as a function argument cannot prove what the user
currently permits. An action may be selected and authorized, then wait in an
outbox while the user pauses proactive behavior or narrows its risk boundary.
Without a durable policy identity, a worker cannot distinguish current
authority from an obsolete snapshot.

## Decision

Each subject has an explicit autonomy-policy projection. Fresh state is absent
and therefore disabled. Only an event whose actor and subject are the same user,
whose structural payload carries the installation authenticator, and whose
expected revision matches the current revision may advance policy state.

The policy records whether proactive execution is enabled plus the deterministic
deliberation boundary: interruption permission, minimum confidence, maximum
risk and allowed side-effect classes. Concurrent updates use optimistic
revisions. If several authenticated updates target the same revision, journal
sequence—not thread scheduling—chooses the first; online projection and replay
therefore converge.

Authorization receipts bind the exact policy event and revision. Action-attempt
admission proves that this policy was recorded, enabled and not superseded
before the attempt. Dispatch rows retain the policy event ID. Acquisition and
content access revoke pending or leased work whenever that ID is no longer the
latest enabled policy. Re-enabling autonomy does not resurrect revoked work;
the action must be selected and authorized again.

## Consequences

- Missing policy, disabled policy and stale policy all fail closed.
- A user pause invalidates queued authority without deleting causal history.
- Projection rebuild is deterministic under concurrent policy updates.
- The policy projection remains independent of the outbox; the outbox derives
  revocation from current policy instead of being mutated during historical
  replay.
- This boundary does not pretend to recall an external operation that already
  crossed the adapter boundary. A separate started/uncertain dispatch protocol
  is required before any real adapter is connected.
