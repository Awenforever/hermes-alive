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
