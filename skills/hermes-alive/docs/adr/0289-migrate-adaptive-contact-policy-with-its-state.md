# ADR-0289 — Migrate adaptive contact policy with its state

Status: proposed. Required before an adaptive legacy profile can cut over
with its timing behavior preserved.

## Why this differs from fixed quiet hours

The legacy dynamic policy can close outside the fixed interval and open
inside it. Its decision uses a local plan, current phase, persisted learned
offsets and explicit exceptions. The legacy function `shadow_decision` advances
and saves state in live and shadow modes. Calling it during new-engine startup
would create a writer to the rollback source even in a preview. Importing
the fixed times from the same profile would lose active behavior. ADR0288
covers the fixed option and currently requires a deliberate replacement for
legacy adaptive timing.

## Proposed cutover

Read and validate an isolated copy of the effective legacy configuration and
current dynamic state. Bind the proposed import to the owning profile and
show its actual contact behavior in setup. Capture only the state needed to
reconstruct the plan and its timing adjustments, with source version and
fingerprint. Keep that state private. Confirm preserving adaptive timing,
choosing a fixed window or allowing all hours. Treat future learning and
ordinary conversation use as separately guided choices.

Keep the old files immutable for rollback. Only the active new owner writes
the new checkpoint. Activation and recovery must check its integrity and
current configuration. Malformed or unavailable state withholds proactive
contact and gives the owner a clear status. No replacement model, legacy
watcher, second queue or hidden notification bypass belongs to this import.

Advance the new timing projection at the existing host wake. The adapter
handoff check must be synchronous and bounded and use the current window and
exception, with the existing permission/deadline check. This preserves useful
background work while quiet. Any new interpretation of sleep/wake requests
must use the admitted owner turn, with explicit exceptions distinguishable
from quotations, incidental mentions and synthetic reports. Expiration and
owner correction must be reversible and survive restart.

## Evidence required

- Replay identical civil-time instants from read-only snapshots through the
  released policy and the candidate. Compare awake/protected decisions at the
  start and end, midnight, current override, learned-offset rollover and DST.
- Exercise explicit exceptions and counterexamples using real Core turn
  admission and no broad history import. Show correction and expiry.
- Test both restart and rollback with running work, and retain the original
  legacy config/state bytes. Prove only one gateway process can own the chosen
  generation and that no previously withheld draft is replayed.
- Compare decisions without actual delivery before proceeding to a separately
  authorized channel trial. Record differences and why each is intended.
