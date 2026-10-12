# ADR-0037: Bounded shadow comparison through Hermes

Status: accepted for isolated shadow execution

## Decision

Connect meaning, a natural model rendering and independent review in one
unscheduled comparison operation. The deterministic rendering is retained as
the baseline. The result exposes the encrypted candidate and authenticated
review receipt for evaluation; it has no delivery capability.

Hermes owns auxiliary routing, model selection, credentials and fallback. Use
separate `alive_semantic_render` and `alive_semantic_review` task names and
optional model selectors. Attribute the response's actual model together with
Hermes' reported provider. Missing actual route information fails visibly.

Independence domains are supplied by a host-controlled resolver keyed on
actual provider and response model. An unknown model family cannot acquire
independence by receiving a different alias or task name. The reviewer does
not receive the renderer's model identity. Distinct executions and the
ADR-0035 model/domain checks remain mandatory after fallback.

Before any provider request, append a durable operation-start event. Reusing
that operation fails before another call, including after a crash. A caller
must explicitly choose a new operation to retry unresolved work. Each
operation makes at most two calls; Hermes may apply its own configured
transport retries/fallback inside a call. Bound prompt/response sizes, output
tokens and per-call wall time. Propagate task cancellation and record it.

Treat meaning and candidate text as untrusted data in both prompts. Parsing
rejects duplicate JSON keys, extra fields, missing atom reviews, non-boolean
flags and invalid risk classes. Schema compliance remains distinct from
semantic quality. Revalidate the selected intent and content after both
asynchronous calls before accepting a candidate or review.

Stage receipts store status, actual model and exception class only. Private
prompts, responses and provider exception strings are excluded from the
journal. Candidate text remains in the erasable vault.

## Evidence and remaining work

The supported production auxiliary interface was inspected read-only and
accepts `task`, `model`, `timeout` and `route_info`. Injected execution tests
exercise both calls, actual-model attribution, duplicate-operation prevention,
malformed review, self-review, provider failure, missing route metadata,
timeout, cancellation and intent changes during review.

These tests validate orchestration and failure handling, not model quality.
No real-provider corpus was run by this milestone. Human calibration,
qualification-sized multilingual replay, user correction controls and a live
canary remain open. Production scheduling is still disabled for this path.
