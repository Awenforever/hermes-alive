# ADR 0267 — Recall the question, not the execution protocol

Date: 2026-10-28. Status: diagnosed boundary; integration proposal, not implemented.

## Observation

The actual Core worker initialized the configured external Holographic provider
successfully, including NumPy. Its prefetch input nevertheless contained 2,891
characters of task and execution protocol and returned no facts. In that same
worker, the same provider could recall the synthetic target fact from a short
semantic query. That diagnostic did not replace the original worker answer or
inject a fact into the worker request: the original integration case still fails.

r289 isolates the input boundary further. With real unmodified Core's job prompt
builder and the same provider/database, the inputs behave as follows:

| Input | Characters | Target recalled |
|---|---:|---|
| Short semantic question | 26 | Yes |
| Natural question | 48 | Yes |
| Core cron framing plus semantic question | 1,153 | No |
| Core cron framing plus natural question | 1,175 | No |

The reviewed catalog provider 0.18.3 and maintainer tip 0.20.1 exhibit the same
result. This is a synthetic provider-library counterexample, not a production
incident, generic retrieval benchmark or proof that all providers fail. It proves
that merely shortening Alive's own prompt cannot establish this integration.
Core's automatic prefetch uses the complete user-message text. The external
provider's relevance gate considers informative query terms, including protocol
terms; successful initialization alone cannot qualify useful recall.

## Proposed boundary

Preserve Core ownership of the configured memory provider, identity, storage,
retrieval and provider dependencies. Native recall should use Core's public
MemoryManager/provider lifecycle with a bounded semantic question, separated from
tool permissions, source fingerprints, clocks and execution protocol. A returned
fact is advisory evidence, not an owner statement, permission or execution result.
Do not copy external memory into a second permanent Alive memory store.

This needs its own first-guidance read choice. Existing curated-USER consent does
not authorize external-provider reads retroactively. Keep the selected personal
profile, subject and current read grant bound throughout physical retrieval;
revocation, forgetting, shutdown and profile changes must fence use of results.
Use the existing bounded physical context-read lifecycle. Do not spawn an
unowned reader or replace Core's context engine. Core provider side effects must
be understood, including recall bookkeeping and optional remote reranking.

Automatic Core worker prefetch remains a separate boundary. Do not monkeypatch
Core, wrap a particular provider's query parser, strip keywords from arbitrary
messages, adjust a private provider threshold, move text past a truncation limit,
or insert a known answer just to make this counterexample pass. A supported Core
semantic-query boundary or normal authorized explicit memory tool call needs
actual integration evidence before this worker gate can close.

## Required qualification

Exercise actual installed Native cognition receiving appropriate external recall,
provider opt-out and missing dependencies, scope and grant changes during reads,
cold restart, content deletion and no recall-body duplication. Verify that private
facts cannot enter public discovery requests through this path. Use more than
one semantic question and counterexamples; an empty result must mean no usable
evidence returned, not evidence that the owner has no relevant memory.

Retain the actual-worker failure and the Core-framing counterexample. A passing
short-query control must never relabel either as a passing end-to-end workflow.
No Core, provider source or production configuration was modified for this ADR.

## Reproduction preserved in the repository

`__tests__/probe_core_memory_framing.py` uses a fresh synthetic profile, the real
Core prompt builder and an unmodified provider checkout. Run it in the admitted
Core/provider dependency environment with `--core`, `--provider-source`,
`--legacy-source` and a new `--report` path. It requires both raw questions and
their normally framed versions to recall the target. r291 recorded both short
controls passing and both framed recalls missing, and correctly exited 1 with
`CORE_MEMORY_FRAMING_GATE=FAIL`. This preserves a failing integration gate rather
than converting a known limitation into a green expected-failure acceptance.
The probe checks the library boundary; the earlier actual-worker failure remains
necessary evidence for the complete workflow.
