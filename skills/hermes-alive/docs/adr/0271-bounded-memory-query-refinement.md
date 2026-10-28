# ADR 0271 — Bounded, model-guided memory query refinement

Date: 2026-10-29. Status: candidate; controlled and unchanged real-task
qualification required. No production change.

## Evidence

r323 used the same synthetic assignment as r318 after the work-context fix. The
first real model query combined the usual teaching aid with topics and formats.
The configured public provider returned no context. The model's later focused
query did recall the fact, but the first Core job had already produced a generic
activity. The task therefore remains a failure. Injecting the fact, shortening
the fixture request, lowering the provider threshold, or silently enabling a
different backend would hide the actual boundary rather than solve it.

## Decision

On a fresh private reasoning context, ask Core's model for one focused retrieval
question or entity/topic phrase. If Core returns no usable context, give that
result and the previous query back to the same configured model. It may stop or
choose one meaningfully different query. There are at most two provider reads
for a fresh context. A declined or malformed proposal is not automatically
retried. Repeating the same query with only case/whitespace changes causes no
second read. Provider-unavailable, oversized-context and builtin statuses do not
invoke reformulation.

No usable result is not proof that the memory does not exist; the feedback says
so explicitly and does not invent the backend's reason. Core still owns
timeouts, concurrency, physical prefetch threads, provider configuration and
model fallback. This is a bounded new semantic question, not a transport-retry
queue. No new provider, vector index, credential or database reader is added.

The transient cache retains the final admitted question. An unchanged context
can read it on a later natural wake without repeating model planning; source or
grant changes still fence the read and returned evidence. Retrieved advice is
published once, after this bounded deliberation, before private work planning.
Query bodies and empty-result histories are not persisted in the structural
journal. The existing fingerprint-only observations remain.

Work handoff records also retain the advisory-context fingerprint and evidence
identifiers before Core IO, without raw advice or additional authority. This
preserves attribution if the process stops between submission and the later
decision receipt. Existing protected Core task records own generated step text.

## References and limits

This uses the retrieval-feedback/query-rewrite pattern described in the
[LangGraph retrieval-agent tutorial](https://docs.langchain.com/oss/python/langgraph/agentic-rag).
[Azure's query-rewrite documentation](https://learn.microsoft.com/en-us/azure/search/semantic-how-to-query-rewrite)
also distinguishes model-generated alternate queries from changes to the index.
These references are design context, not additional runtime dependencies or a
claim that bounded reformulation guarantees recall. Their code and services are
not installed or called by Alive.

Qualification must cover successful reformulation, explicit stop, repeated query,
malformed reformulation, old grants and unchanged-context budgets with the real
Core provider. Rerun the unchanged real assignment and inspect actual work.
Longitudinal noise, provenance-dependent erasure and general worker-provider
qualification remain separate requirements. The automatic Core cron-framing
counterexample remains a failing probe.
