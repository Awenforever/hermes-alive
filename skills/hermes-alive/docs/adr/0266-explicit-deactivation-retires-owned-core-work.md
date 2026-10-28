# ADR 0266 — Explicit deactivation stops future owned work and preserves results

Date: 2026-10-28. Status: implementation under isolated qualification.

The owner chose cancellation of work that has not started and a stop request for
running work when Alive is disabled or uninstalled. Existing results remain.
Ordinary upgrade preserves ongoing tasks and progress. These are different
lifecycle operations, not interchangeable meanings of an unload callback.

Core unload does not communicate a reason to plugin callbacks. Read Core's
public profile-selection state and authoritative manifest aliases to establish
explicit deselection. A selected plugin reloading does not retire work. Never
infer uninstall from a momentarily absent source path during file replacement.
The explicit owner pause and runtime-uninstall paths invoke retirement directly.
Startup failure cleanup does not silently become an owner cancellation.

Before inventory, disable the existing signed autonomy policy to fence new
handoffs. Enumerate signed work records, verify each Core definition fingerprint,
and group parent work with its inspection. Do not cancel a job based on its name.
Pause Core schedules without removing records, notepads or outputs. Persist stop
intents before cancellation IO. For running work, recover its existing Core
admission and request cancellation through Core; do not submit replacement work.
An acknowledgment is not evidence of termination or rollback. Missing or changed
jobs, unavailable owner RPC and lost answers remain explicit attention states.

Core's synchronous unload callback cannot await an asynchronous cancellation.
The bridge prepares durable fences synchronously and retains a finite async IO
tail on its binding. This is neither a business executor nor a retry scheduler.
If it cannot complete, retained stop records and unknown outcome are the truth;
do not claim that an interrupted operation was undone. Runtime uninstall refuses
to delete its code while cancellation outcome needs reconciliation. Repeated
observation does not replay an uncertain cancellation attempt automatically.

Qualification must exercise actual Core queued and running work, current-owner
pause, explicit deselection, uninstall, unchanged-selection reload and upgrade,
cold record/key/result preservation, unrelated jobs, and lost cancellation
answers. These controlled synthetic cases do not qualify daemon control,
cross-platform installation, real-model judgment or production migration.

## Qualification evidence added 2026-10-28

r279 failed on a fixture's nonexistent Core `paused` field; its failed record is
retained. r280 corrected the assertion and exercised disable, pause, uninstall
and unchanged-selection reload against real Core jobs/ticks. r281 then qualified
five independent actions (adding ordinary runtime upgrade), each with a fresh
cold reader: stopped work did not call the worker, reload/upgrade work actually
completed, existing results and identity keys remained, and an unrelated Core
job with an Alive-shaped name was unchanged. Existing execution-control and
unchanged-wait tests also passed. r282 exercised a real running Core agent:
pause and explicit deselection requested cancellation via Core's admission RPC;
the controlled lost-answer pause remained unknown and did not redispatch on a
repeated pause. Workers stopped without writing their target, with cold checks.
All containers terminated and were absent before these results were recorded.
These are synthetic-provider Core library/in-process checks, not a production,
daemon, public installation, Windows or WSL acceptance claim.

Final bounded rerun r284 also includes the explicit profile CLI-disable path
(six actions and six cold readers), normal manual work and file inspection as
positive controls, portable legacy CLI behavior, and explicit parent-observed
running-stop proof markers. All passed against the final runtime. A guard must
distinguish an authenticated ordinary producer from an unrelated job: both used
to return None, which would incorrectly block valid manual work once reserved
producer names were fenced. Verified producers now return a distinct affirmative
result after the Core definition and stop checks. No name grants ownership.
