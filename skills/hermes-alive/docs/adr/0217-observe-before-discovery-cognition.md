# ADR0217 — Observe public listings before spending discovery cognition

Date: 2026-10-24 (Asia/Shanghai), Codex.
Status: phase boundary implemented; waiting integration and qualification open.

The ordinary native host currently invokes configured discovery preparation
before the autonomous cycle's reconsideration check. That preparation combines
search, model selection and page reading. A later wait check cannot prevent an
already-spent selection call. Merely continuing after a content rejection would
also regenerate against unchanged input and could repeatedly consume models.

Split the existing preparation into `observe` and `reason`, retaining `__call__`
as their composition so existing callers keep their established behavior.
Observation collects only approved public search listings, preserving the same
durable host receipts, URL checks, retention and source ingestion. It does not
perform model selection, create a model-derived inquiry or fetch linked pages.
Research-mode receipts still precede the original search start: moving these
after it would reinterpret historical cycles or silently disable those modes.

An ephemeral observation belongs to its exact preparation instance, operation,
owner binding and generation. A new observation or unload retires earlier tokens.
Cognition rechecks consent, binding and retained source material before calling
the model. Unload does not forget a physically outstanding reader; settlement
and physical read locking remain owned by the existing read wrapper.

A keyed listing fingerprint covers approved queries, exact retained observation
identities and reading-mode options, excluding per-operation receipt IDs. Only a
fully successful listing collection has a fingerprint; partial/refused/failed
collections are unknown, not evidence that the world has not changed. Successful
empty listings remain distinguishable from failures. This fingerprint says
nothing about unread page bodies, all possible sources or private conversation.
It grants neither suppression, authority nor delivery.

This is groundwork, NOT completed durable waiting. The native host still uses
the composed entrypoint. Next integrate change-sensitive cognition eligibility
with owner/context/agenda changes, fairness and bounded revisit deadlines. Do
not globally hide source evidence, change its historical truth, create another
physical FIFO, or silently treat rejected content as successful silence.

Two actual native-Core authoring probes against public synthetic replay produced
unsupported explanatory additions; separating recipient body from Core's final
tool response improved an output boundary but did not prove factual quality.
Consequently no alternative native authoring backend is adopted and no quality
review is removed. This is negative evidence, not a passing recommendation round.
