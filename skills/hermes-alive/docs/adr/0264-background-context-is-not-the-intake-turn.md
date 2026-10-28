# ADR 0264 — Ground retained instructions in their originating turn

Status: bounded installed-Core temporal/cache qualification passed; real-model
positive/wait qualification pending.
Date: 2026-10-28.

The r260 real-model rerun kept the same owner questions. Intake correctly saved
the two-step task without a made-up deferral or deadline, and main distinguished
project A from the foreground project B. Nevertheless, the first autonomous
decision called the later background wake the registration round. It chose wait;
the following cognition calls repeated that interpretation. Five cycles created
no jobs and the work gate failed. This is a genuine temporal-grounding failure,
not provider unavailability, completed work or an excuse to advance the clock.

The execution worker already has an explicit later-background-turn envelope
following ADR0258. Decision input had only a generic warning that the original
request was historical; cognition supplied an as_of timestamp but no explicit
current-owner-turn boundary. Apply the same source/turn distinction before work
selection as during execution. Do not solve it by matching particular language
phrases or silently stripping original constraints from their retained source.

The decision now has work_turn_context identifying this background invocation,
its actual observed time and host operation, with no current owner turn supplied
and no new authorization. Its instructions distinguish an origin-bound
registration condition from continuing restrictions and unmet owner-start or
approval requirements. Cognition's stage contract likewise distinguishes retained
owner sources from a current owner turn. The worker retains its existing later
execution envelope and the same no-current-owner-turn distinction.

Decision-context version 2 participates in the source basis. Old interpreted
waits are not silently reused under the new context protocol. Existing work
intent IDs, unknown handoffs and Core records are not recreated or reset. This
is cache provenance, not an authorization upgrade or permission to retry work.

Controlled cases must inspect the actual decision/cognition envelopes, retain an
explicit owner-start wait, and ignore a valid old-context wait receipt when
evaluating the new context version. Both ordinary work and distinct continued
steps must still use the real Core path. Re-run the unchanged real-model task,
then separately verify an owner who explicitly requires a further start message.
Do not mistake a later invocation for satisfaction of an unmet owner condition.
The full initiative, retention, lifecycle, fleet and production gates remain open.

r261 passed six controlled actual-Core cases and cold checks: ordinary execution,
explicit owner wait, distinct continuation, malformed and out-of-scope proposals,
and partial outcome. Assertions inspect the actual planner/cognition envelopes.
A valid signed old-context wait is retained but is not reused under context
version 2; the new decision still honors the owner's unmet start condition.
Original process exit 0, container die 0/destroy/absence and clean Core supplier
were checked before report inspection. These controlled judgments do not prove
that a real model will interpret the same distinction correctly.

The unchanged-driver real r262 run passes the bounded continued-work journey.
Main records no unrequested date, retains project A while the foreground moves
to B, and can query the original later. Three Native wakes use the inherited
DeepSeek main model: first submit step one, then a distinct second step, then
wait because both are attained. Two actual Core jobs write each requested file
once and read it back; the first file's modification time stays fixed, B remains
untouched, and no third job, automatic closure or external send occurs. A final
fresh-history main query reads owned records without changes. Its reply is
verbose and exposes implementation/status keys; this is a dialogue residual,
not evidence of polished sharing or whole-assistant acceptance.

The original process exits 0; actual container die 0/destroy/absence are confirmed.
Before reading any model body, all six scanned files pass credential-disclosure
audit and the temporary model projection is removed. Core remains clean and the
isolated gateway stops normally. This positive case does not establish that a
later wake satisfies an explicit owner-start requirement; the independent r263
counterexample remains a separate test. No production or fleet claim follows.

That independent r263 counterexample subsequently passes its waiting boundary:
two Native wakes, one model wait decision and two cognition calls submit zero
jobs and make no file or outward-message effects. The task remains unchanged;
the fresh final main query is explicitly not a start instruction. Main and
Native preserve the owner's requirement for a later explicit start, even with
an existing file-scope grant. Original exit 0, actual die 0/destroy/absence and
six-file credential audit false/projection removal precede body inspection.

Main's final reply still presents the original project as a further alignment
point although that binding is already retained; foreground B is not a new
permission condition. No actual rebind or scope change occurs. Keep this and
the verbose/status-key wording as dialogue limitations. The positive and wait
pair qualify these bounded work decisions, not universal source semantics or
zero-error conversation/sharing. Later empty-scope changes have their own
controlled Core qualification rather than being silently called this exact run.
