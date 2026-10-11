# ADR-0021: Model selection is gated and non-executing

Status: accepted for the shadow kernel

## Context

ADR-0007 defined bounded model deliberation, and ADR-0020 produced a complete
cycle that deliberately selected silence. A real selector still needed to
prove provider neutrality, fallback attribution, prompt privacy and enforcement
of both deterministic policy and exploration without accidentally executing the
selected action.

## Decision

An unscheduled selector reads a durable frame and its latest matching,
successfully projected exploration receipt. It sends only gate-admissible
candidates to Hermes' configured auxiliary model route. Candidate bodies are
untrusted data; rejected candidates are absent from the prompt. The request and
response are bounded and the response must be an exact JSON object containing
one supplied candidate ID and a rationale.

The actual model reported by the successful Hermes response is authoritative;
the requested alias is not attribution. Alive owns no provider credentials or
fallback list. The proposed selection is independently revalidated against the
stored frame and exploration result before an encrypted durable selection is
written.

Raw prompts, responses and provider error bodies are ephemeral. Durable
receipts contain only attempt status, frame/gate IDs, actual model, selected ID
and error class. Operation IDs are single-use, internal retries are bounded and
semantic reuse fails closed.

A validated selection is still only an intent decision. This component cannot
create an action attempt, send a message or execute a tool. It remains
unscheduled until held-out replay and shadow evaluation justify invocation.

## Consequences

- A fallback selection carries the fallback model's true identity.
- Policy- or diversity-rejected content never reaches the selector model.
- Invalid model output can safely retry or terminate without an external side
  effect.
- Selection quality and action outcome remain separately measurable.
- Action attempt creation, send-time revalidation and execution need their own
  authority boundary rather than being added to this selector.
