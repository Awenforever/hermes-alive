# ADR 0172: bounded native reasoning-only continuation

Date: 2026-10-18. Status: implemented; isolated qualification in progress.

## Measured failure

Two opt-in private-profile trials failed at initial opportunity synthesis, with
one started native request, no observed post event and max_iterations_reached.
They used different configured generation providers. Neither proves a 403 or
unavailable provider; both remain failed trials, not clean acceptance rounds.

Controlled HTTP against the actual current Core reproduces the same diagnostic
shape: a length response is handled before post_api_request; a one-iteration
agent cannot run Core's continuation, then may make an auxiliary summary request.
That summary is not the original request's final response. Main api_calls does
not count every physical auxiliary request. Matching diagnostics alone does not
establish either live request's raw finish reason.

## Decision

Use the existing host-owned llm_execution middleware as a read-only observation
point in the private API worker, before Core's response-intake continuation logic.
Pass the same request downstream exactly once and return the identical response.
Scope lookup precedes response inspection; retain bounded safe shape metadata,
not text, reasoning, prompts, credentials, arbitrary labels or provider errors.
Only an assistant length response with no content, tool calls or legacy function
call can close a request as no_output_length. Unknown shapes remain unqualified.
An observation error invalidates our proof without changing provider behavior.

Allow at most two agent iterations within the existing owned process lifetime and
run-time budget. Core still owns continuation, reasoning settings, routing and
fallback; no production configuration changes or competing model registry.
Core may boost the initial output allowance on continuation; the request's
max_tokens is not an aggregate token ceiling. Worker process lifetime remains
bounded. Exhaustion can still trigger Core's additional auxiliary summary; it is
never accepted as a final completion and logical/physical counts stay distinct.

The sole accepted final still needs exactly one native post completion with
finish=stop, no tools, exact text/hash/model/provider and a completed,
uninterrupted, untransformed, unreused Core result. Missing/unclosed attempts,
multiple final replies, partial-text stitching and summaries remain failures.
The execution observer is not a replacement final-completion authority.

Core may omit result transcript coordinates after continuation rewrites the
original user row. Only the isolated worker can supply its directly owned live
agent's session/task/turn binding. This path is restricted to exactly two observed
attempts: one no-output length and one final completion. The owned binding must
match both the original scope and final post identity. A wrong result coordinate
is never overridden, and no ID is copied from the post record into a result.
Evidence records turn_identity_origin explicitly; ordinary results retain the
existing result-envelope origin. No sending permission is created.

## Verification and limits

- Local completion and real-child protocol suites pass, including wrong/absent
  binding, foreign response non-inspection, downstream error propagation, partial
  text/tools/function/role/unknown shape rejection and middleware disposal.
- Actual Core controlled-HTTP focused suite passes: normal routing, primary 403
  fallback, reasoning-only continuation, rejection of partial-text/always-length,
  host snapshot/current-owner revocation, client privacy/header policy and replay.
  First focused tree 7c01d97 failed reasoning continuation due to the omitted
  result coordinate; corrected runtime/tests tree e797f18 passes. Preserve both.
- No paid model, private chat, route authorization, transport or production send
  is used by these controlled tests. This is not proof of recipient usefulness,
  fresh dependency installation, ten clean rounds or complete longitudinal memory.
- Real profile revalidation and full canonical portable CI remain pending at
  this writing. A content-length failure still needs an evidence-based output
  contract/budget correction; do not simply accept concatenated fragments or add
  indefinite retries/review layers.

Continue the bounded personalization/discovery/feedback milestone, rather than
another infrastructure expansion. FIFO remains the channel enhancement's duty.
