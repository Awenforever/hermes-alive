# ADR-0018: Model synthesis is advisory and Hermes-routed

Status: accepted for the shadow kernel

## Context

Retained conversation evidence is useful only if it can become a small number
of durable, reviewable hypotheses. The retired Dream path mixed transcript
reading, provider execution and direct state mutation. That made model output
an authority, duplicated Hermes model configuration and made failure or
fallback attribution difficult to audit.

Pure deterministic extraction is not a sufficient replacement: durable user
preferences and self-model hypotheses are semantic, while a growing list of
phrase-specific rules would be brittle and language dependent. Conversely, a
model response cannot be trusted merely because it is valid JSON.

## Decision

Alive exposes a provider-neutral synthesis boundary that:

1. requires separate per-user retention and learning consent before gathering
   any evidence or calling a model;
2. reads only decryptable, unexpired retained conversation excerpts through a
   newest-first subject/type index and caps scanned records, selected events
   and total text;
3. calls Hermes' configured auxiliary model route, with no plugin-owned API
   key, provider client or fallback list;
4. labels excerpts as untrusted data and requires a strict bounded JSON result;
5. records the actual model reported by the successful Hermes response, never
   inferring attribution from the requested alias;
6. validates candidates independently against evidence, kind, schema, score,
   expiry and finite-JSON contracts, so one bad candidate cannot cancel valid
   siblings;
7. admits every surviving candidate only through `ConsolidationService`, where
   it remains an expiring `PROPOSED` memory until the user explicitly accepts
   it; and
8. persists only structural receipts and encrypted proposals. Raw prompts,
   responses and provider error text are not journaled.

An operation identifier is single-use. A prior receipt prevents a retry from
calling the model again, avoiding duplicate or semantically divergent
proposals after ambiguous caller retries. Internal parse retries are bounded
and share one evidence window and timestamp.

This decision adds a callable boundary, not a scheduler. Automated invocation
remains off until a sanitized replay corpus and longitudinal metrics show that
the proposals are useful, non-invasive and reviewable.

## Consequences

- Hermes remains the owner of model selection, credentials and provider
  fallback behavior.
- A fallback response is attributed to the model that actually answered.
- Model creativity can help interpret meaning without granting write
  authority over memory or other actions.
- Erased, expired, corrupt or non-retained evidence is unavailable to
  synthesis by construction.
- Strict schema rejection is safe because it rejects only a synthesis attempt;
  it does not block normal conversation or legacy Alive operation.
- Scheduling, batching frequency, user review UX and quality thresholds remain
  separate future decisions backed by replay evidence.
