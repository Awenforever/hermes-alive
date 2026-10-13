# ADR-0061: Cognition preparation is not a forced choice

Status: accepted for explicit, unscheduled shadow planning

## Context

The coordinator joined durable framing, active-agenda validation and exploration
but unconditionally closed with safe silence. The provider-neutral selector
existed separately. Thus the coordinator itself could not make a model judgment,
and replaying its audit baseline after a later model choice incorrectly inspected
the latest selection as if it were that old baseline.

An attentive assistant must be able to choose a useful initiative or deliberate
silence. A preparation step must not silently dictate the decision, and a
historical audit result must not masquerade as current intent.

## Decision

- `prepare` persists and validates the candidate frame and exploration result,
  returning an immutable preparation with causal event IDs, owner and sensitivity.
  It makes no selection and invokes no model, channel or tool.
- `plan_safe_silence` remains the explicit deterministic audit close. Its return
  refers to that exact historical baseline receipt, not a later selected intent.
  Re-reading an existing baseline cannot override a subsequent model selection.
  Creating a new audit baseline after an existing intent is refused; use a
  separate audit cycle instead of silently superseding current intent.
- `plan_with_model` composes preparation with the existing Hermes-neutral
  selector. It receives a model capability explicitly, carries optional requested
  model selection and delegates provider/fallback behavior. Results retain the
  actual response-model attribution and durable model receipt IDs.
- When the exploration result admits only silence, the coordinator closes it
  without a model call. A one-shot candidate iterator is consumed once, not
  prepared again for this shortcut.
- A model failure propagates with its real failure/start receipts. It is not
  rewritten into a successful model decision. A separate explicit audit close
  may be made if no intent exists. Default model operation identity derives from
  the cycle, so repeat invocation after cancellation/recovery refuses another
  spend under ADR-0060. A new explicit operation is not implicit retry authority.

A selection is an intent only. This coordinator cannot authorize an action,
create an attempt, dispatch, send, execute a tool or activate a memory proposal.
No production watcher or automatic schedule is connected by this change.

## Evidence and remaining work

The composed contract uses the real discovery ingestor, encrypted opportunity
agenda, coordinator, selector, journal and ordered recovery supervisor. Only the
model response is a deterministic fixture. It covers causal event linkage,
preparation/replay idempotence, choosing an opportunity, true model attribution,
deliberate model-selected silence, no-call policy silence, baseline isolation,
route/output failure, restart refusal to repeat a model operation and exclusion
of private fixture text from the journal. It does not prove a real provider's
judgment or user benefit.

Candidate generation and dimension assessments are still supplied by the caller;
the fixture labels its estimates as model judgments, not measured outcomes or
inferred user authority. Meaningful event-to-candidate interpretation, explicit
user policy integration, model budgets, human-calibrated longitudinal replay,
live shadow orchestration and real delivery qualification remain required.
Repeated internal selection alone must not be scored as exposure, attention or
benefit. Existing send-time authority and outcome evidence boundaries still apply.
