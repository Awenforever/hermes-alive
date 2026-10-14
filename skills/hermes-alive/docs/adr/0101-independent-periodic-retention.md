# ADR 0101 — Privacy cadence is independent of proactive-send cadence

Status: running-watcher periodic composition under isolated qualification;
no production activation or fully disabled-service scheduling claim.

## Connected loop

The existing watcher now attempts local retention maintenance before its decision
enablement/adapter gates and during its normal one-second wait loop. A five-minute
monotonic privacy cadence is separate from the configured proactive interval.
Pausing messages or selecting a long delivery interval therefore does not itself
disable retention work while this watcher remains running. No new cron job, OS
service, installation default or kernel consent is introduced. A missing kernel
database returns without creating one.

Maintenance runs in an owned shielded worker task, off the gateway event loop.
Cancelling a tick does not cancel that worker or launch another one; subsequent
checks join the same handle. Direct cancellation of the wrapper does not establish
that its thread stopped. That completion remains unknown and blocks further
proactive work without guessing/restarting. Normal termination clears the handle.
This is not hard-process-shutdown qualification or an arbitrary abandoned-thread
recovery mechanism; a stopped/uninstalled service cannot run this loop.

An erasure failure or unresolved dependency pauses subsequent proactive decisions
and reports a structural error. Successful unchanged empty reports are not written
on every poll. No metadata cleanup result grants permission to send or learn.
Long-running model/discovery work or a slow sweep can delay the next poll; five
minutes is a cadence, not an absolute deletion deadline. Read-time expiry denial
still applies independently, and real-time/large-history costs remain required.

## Evidence, not only scheduler spies

The new test verifies absent-store no-op, paused decisions, enabled/no-adapter
continuity, repeat interval exclusion, a long send interval not disabling upkeep,
unresolved-state rejection, parent cancellation retaining the live task, and direct
wrapper cancellation not causing a duplicate worker. Threads are controlled and
released within bounded test time; no real provider or model is called.

It also invokes the actual retention/storage APIs through a disabled watcher over
an explicitly created synthetic kernel. A stored expired sentinel is physically
erased and remains labelled automatic expiry, not explicit user forgetting. This
tests callback composition, not just counting an injected cleanup function.
Existing discovery-once control and twelve sleep/quiet-policy scenarios protect
the legacy decision/wake path. A temporary test indentation error is corrected
before executing the strengthened actual-storage fixture; it is not a passing run.

First Linux invocation stops in an old sleep-policy fixture: it inherited the
carrier Hermes home and attempted a control.lock write on the read-only scratch
mount. No production mount is present. The test now owns its home/runtime in a
temporary directory instead of reading/writing a caller's real control location.
This failed setup remains failed, not a runtime policy defect or a green batch.

## Immutable anchors and qualification boundaries

Initial snapshot tree edb5347da926c3007de71fee92912dfded647daa, archive SHA256
984797cede51b6ac1759eab0d9f7f1a115ca1723768b09b128aa2b6253e72f6c.
Final runtime/test tree 2a2876f2967e3b22849792da49a3015e8b6632da, archive SHA256
ae4ea60b5f7cc03e6b8e65e35d7516b8fa45bd9d8cbadef0e26e3544c5e11a79.
Focused Windows scheduling/storage and discovery-control tests pass; final broad
Linux results are recorded only after authoritative terminal verification.
Final isolated container alive-periodic-retention-full-20261014-r2 is verified
exited 0, from 2026-10-14T02:50:16.944230394Z to 2026-10-14T02:53:10.800268489Z.
The watcher scheduling/actual-storage suite, discovery-once control, all twelve
sleep/quiet scenarios and ALL_KERNEL_SUITES_PASSED=67 complete successfully.
These are bounded internal and source-command tests, not a running installed
production gateway, real channel delivery or ten zero-error actual Alive calls.

No live model/HTTP calls: totals remain 95 logical / 107 observed HTTP attempts.
No real sends, private chat access, production data/config/model/channel/auth or
restart change, wmw/other-plugin change or credential export. README/main/releases
and public version remain unchanged. Tests erase only generated synthetic content.

Actual gateway registration when a plugin/channel is fully disabled, task teardown,
immediate command subscribers, transitive model-derived copies, external/Halo
storage, ledger/clock integrity, large-history performance, real receipt capture
and longitudinal utility are still unqualified. Keep the complete layered-memory,
sustained-agenda, feedback/adaptation, migration/rollback, portable lifecycle and
production-acceptance scope intact; do not label this as complete forgetting.
