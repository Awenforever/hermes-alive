# ADR 0102 — A watcher task handle is not cross-instance maintenance ownership

Status: shared OS-lock handoff under isolated qualification; no production reload.

## Gap and correction

ADR-0101 tracks a shielded task inside one watcher. A replacement watcher has no
access to that Python field while the old worker may still be running. The existing
watcher singleton lock protects run(), but is released when its owner exits; it
must not be assumed to establish the termination of a detached cleanup thread.

resume_retention_maintenance now acquires the same real recovery.lock used by
KernelRecoverySupervisor before any runtime/projection/erasure setup. Nonblocking
failure returns maintenance_busy=1 rather than claiming completed privacy work.
The caller treats busy as non-ready and does not continue proactive delivery.
It re-observes lock ownership promptly instead of waiting a full maintenance
interval or starting another cleanup body. Identical busy reports are quiet;
actual completed erasure/error changes remain visible. Normal release permits
another maintenance cycle. No age-based lock stealing, PID heuristic, blind
timeout restart, new OS service or weakened privacy validation is introduced.

The lock file's continued existence is not a live-owner observation. Only actual
lock acquisition/failure governs this boundary. Startup recovery retains its
existing bounded wait semantics on that same lock; it does not run concurrently
with a periodic erasure body. No process/async cancellation is upgraded into a
proof of stopped thread work.

## Evidence and scope

Focused Windows tests run two watcher objects using the actual lock wrapper and
a controlled cleanup body. Cancelling the old wrapper leaves its worker live;
the new enabled watcher reports busy without reaching adapter resolution or
starting another body. Releasing the actual worker permits one later cleanup.
An existing unheld lock file does not block maintenance.

A separate test subprocess acquires the same OS lock, emits an acquisition
handshake and is checked live. Maintenance must report busy while it holds the
lock and resume after the process releases/terminates. The test preserves the
virtualenv executable path, hides Windows process windows, and bounds handshake/
termination waits. It does not use a lock/PID file alone as proof or make provider
calls. Old/new installed gateways, abrupt kill/reboot, network filesystems,
uninstall/path relocation and adversarial lock-file replacement remain unqualified.

Initial runtime/test tree e3abf1434ff5fe9de969c4c3f001ff1a97e36dca, archive SHA256
206f8a53b28eece3912b81d4e02ca38f78246e8ae8670f60c198fecab02b4047.
Final test-strengthened tree cdaa2e072bc1ac374adc4f0f7fcdb4758ef2335c,
archive SHA256 811ad450201ec201076ea96bb6859debadca7e27469cbd54a880fde426fe2584.
The runtime files are unchanged between these snapshots; the latter adds the
subprocess assertion. Windows scheduling/handoff and recovery suites pass.
Linux broad and strengthened focused results are recorded only after terminal
verification; source/index validation is not portable installation acceptance.
Both Linux containers are verified exited 0: the initial broad
alive-maintenance-handoff-full-20261014-r1 reports ALL_KERNEL_SUITES_PASSED=67
and passes the watcher handoff suite; the final
alive-maintenance-handoff-focused-20261014-r2 passes the strengthened separate-
process suite. A git-tree diff confirms runtime hooks are identical between the
two snapshots. No broad test is falsely attributed to later changed runtime code.

No new real model/HTTP calls: totals remain 95 logical / 107 observed HTTP attempts.
No real messages, private chats, production/wmw/other-plugin/config/model/channel/
auth/restart change or credential export. Only disposable synthetic local fixtures
are touched. README/main/releases/public version remain unchanged. Full feedback/
learning utility, sustained agenda, layered/external memory, transitive forgetting,
real host receipts/capture, migration/rollback, portable lifecycle and production
acceptance remain required; do not redefine success as a reliable cleanup loop alone.
