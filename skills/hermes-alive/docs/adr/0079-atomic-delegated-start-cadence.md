# ADR 0079 — Delegated cadence is consumed atomically at execution start

Status: isolated cadence/concurrency regressions repaired; autonomous quality,
qualified host launch and production acceptance remain incomplete.

## Actual gaps

Existing exploration budgets govern novelty/diversity, not how often an owner is
interrupted. Multiple authorized workers could each start without a time budget.
Loading only the committed `2593d0e` begin_execution function into the current
synthetic fixture reproduced two starts despite the fixture grant declaring one
rolling-day start. This isolates the old component; it is not an old deployed
installation test. Fixed execution consumes one start and rejects the second.

Parallel source revalidation also exposed two checkpoint races. Another worker
could satisfy the captured target between loop condition and progress sampling,
causing a false no-progress error. The committed context reader reproduces that
deterministic interleave; fixed readers still reject a genuinely stalled projector.
A further actual traceback identified ReflectionProjection acknowledging an older
record after another worker advanced the checkpoint, raising `checkpoint cannot
move backwards`. That transient exception was being reported as stale source data.

## Atomic cadence

Explicit delegation now includes configurable minimum_interval_seconds and
max_starts_per_24h. Generic safety defaults are one hour and three consumed starts
per rolling 24 hours; they are not inherited personal production preferences.
The public configuration/onboarding integration is still required. Values are
validated as integers with bounded ranges; zero interval still retains a quota.

ExperienceJournal.append supports an internal event factory and read-only
precondition under its existing writer transaction. The outbox timestamps and
authenticates the start at writer-lock admission, then checks the signed grant,
revocation and authenticated owner history on that same connection. Checking and
appending cannot both succeed in independent workers for the final remaining slot.
Factories must not project, acquire a nested writer or do external service I/O.
Identical static event replay does not consume another slot; conflicts still fail.

History is owner-scoped across grants and routes: issuing a fresh grant cannot
reset the count, and another owner does not consume this owner's budget. Exact
rolling-window expiry and minimum intervals are separately tested. The signed
cadence timestamp must match the start envelope. Genuine clock regression fails
closed; ordinary transaction waiting no longer creates a false time inversion.

Consumed starts include unknown or failed later launches. They are not delivery
successes, useful interactions or feedback. This conservative budget prevents
retries after uncertainty from silently flooding the user. A future qualified
reconciliation/override must retain history and explain any reclaimed capacity.

## Monotonic projection acknowledgements

Strict manual checkpoints remain the default: backwards and beyond-journal moves
are rejected. Only the idempotent projections used by current source/authority
readers opt into coalescing after applying a record. If another worker has already
acknowledged a longer prefix, return that higher watermark without changing it.
Progress loops compare against the captured target before calling an unchanged
watermark a stall. This does not accept stale evidence, ignore arbitrary projection
errors or qualify all other projectors for concurrent rebuilding.

## Evidence

- Windows Python 3.14 passes 26 execution modes, including one-slot concurrent
  exclusion and a two-start concurrent positive control through pre-launch checks.
- Dedicated cadence tests cover quota/interval, new-grant non-reset, owner isolation,
  exact window expiry, identical replay, transactional refusal, deterministic
  target satisfaction, genuine stall refusal and strict/coalescing checkpoint rules.
- Journal, delegation, outcome, dispatch evidence and CLI bridge regressions pass.
- Immutable tree `48df6a35c0cf607bdb4adbb3c8f1bbf7f6a0b0cc`, archive SHA256
  `f97b033ff600b1507b73c9cfc5aeff55f7a3dac1fcfe33c32c3e628fa34101d6`.
  Network-none `alive-cadence-offline-20261013-r1` exited zero, start
  `2026-10-13T14:19:46.628005963Z`, finish `2026-10-13T14:20:10.844617482Z`.
  Log SHA256 `39f1c1810be99606514bde1b22a09b35fd886324dbbed77699b4bd53a7657b01`.
  Seven focused suites pass in managed Python 3.13, using only read-only owned
  scratch and writable container temporary files, no network or production data.
  Later documents/manifests are not this snapshot; no full installation qualification.

## Remaining full goal

Permission and cadence do not determine whether a message is true, relevant,
well-written or worth its interruption. Continue source/fidelity and pragmatic
mixed-assertion quality, authenticated onboarding/feedback ingress, trusted actual
delivery and attributed outcomes, then longitudinal agenda/memory/adaptation and
user benefit. Derived-copy forgetting, migration/rollback, latest Hermes lifecycle
matrix and ten real complete zero-error calls remain unproved. No real send,
provider call, release or production activation occurs in this change.
