# ADR 0262 — A rejected proposal must neither execute nor end the host

Status: bounded installed-Core liveness and observation qualification; real-model workflow still pending.
Date: 2026-10-28.

Continued work exposed two general gaps. Invalid autonomous decision JSON, an
out-of-scope execute proposal or an inconsistent wait shape raised ValueError
through host preparation. One unadmitted model proposal could therefore stop
an otherwise useful long-lived host. Separately, wait evidence was attached only
to items without previous Core work. A completed first job could hide the reason
why the next step had not been submitted, both in main status and Native cognition.

## Separate failed interpretation from work and authority

Retain the existing strict action/field/tool-scope/wait validators. They guard
machine operations rather than dictate mail/content interpretation. Move that
normalization into one method, then decline an invalid model proposal at the
boundary. Re-check the current source, policy and guided configuration before
recording a rejection. Its protected structural receipt contains the basis,
operation, actual model if known and a reason code. It contains no raw model
body, task failure verdict, missing-owner-permission verdict or work submission.

The current host cycle can continue without an execution or a replacement job.
Repeated preparation in the same operation does not repeat the rejected model
call. A later existing owner wake may reassess. This adds no timer, retry worker,
fallback model router, canned outward answer or substitute executor. Hermes
continues to own the configured model/fallback and permissions. Transport/API
failures are not relabelled as successful task completion.

## Observe the next step separately from earlier execution

The existing wait evidence reader can return either an attributed model wait or
an authenticated host rejection. Both apply to the next unsubmitted work of the
item, not to the status of earlier Core jobs. A rejection does not prove that the
owner withheld permission or the delegated goal failed. Expose current waiting
evidence through the existing work_status operation and cognition for owned
items as well as items without work. Preserve owner/profile/source restrictions;
pausing does not authorize background body reads.

## Required evidence

Two controlled actual-Core cases return malformed JSON and a terminal-tool
execute proposal under a file-only grant. Neither may create a job/file, persist
raw output or claim a missing owner grant. Start the normal continuous host again
on the same profile: a second rejection must leave that host alive, and its stop
event must finish a completed cycle cleanly. This is liveness, not model recovery.

The existing actual two-step case must also obtain the subsequent wait via Core's
registered main tool with a fresh query turn, and through current cognition.
Earlier work remains completed and exactly two jobs exist. Broader model and
lifecycle acceptance remains necessary; this is not a production qualification.

r257 passed four controlled actual-Core cases and their cold checks: malformed
decision JSON, out-of-scope execute, continued work and explicit owner wait. Both
invalid-proposal cases leave the continuous host alive through a second cycle,
stop cleanly, create no work/job/file and retain no raw invalid output. The
two-step case observes current waiting through the registered main tool and
cognition, without changing earlier completed execution or creating a third job.
Original process exit 0, container die 0/destroy/absence and clean Core supplier
were checked before reading the report. This does not establish correct judgment
by a real provider model or successful correction of a bad proposal.
