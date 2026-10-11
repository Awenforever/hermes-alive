# ADR-0019: Consolidation quality requires complete blinded review

Status: accepted for pre-production evaluation

## Context

Parser correctness does not establish that model-generated memory proposals are
useful. A model can emit valid JSON while inventing facts, retaining transient
requests, surfacing sensitive material, citing the wrong excerpt or flooding
the user with redundant review work. A single aggregate “accuracy” number would
hide these failure modes.

Automatic semantic judges also cannot be the sole authority: they may share the
generator's biases, and phrase-specific deterministic matching would reward a
narrow fixture rather than durable understanding.

## Decision

Every evaluated consolidation run is scored from a complete blinded review:

- every candidate has exactly one verdict;
- every case, including cases with zero candidates, is present;
- every acceptable candidate names one pre-reviewed durable-claim ID;
- a durable claim may be matched at most once per case;
- unsupported, sensitive, transient, duplicate and authority-violating
  candidates remain separate failure classes;
- citation validity is reviewed independently of semantic acceptability; and
- actual response-model identities are retained in the report.

The evaluator reports precision, durable-claim recall, citation accuracy,
unsafe rate, duplicate rate, silence accuracy and review items per acceptable
proposal. It refuses incomplete reviews or cross-case matches.

Before scheduled shadow evaluation can even be considered, one reviewed cohort
must contain at least 100 cases and 20 durable claims, with precision >= 0.90,
recall >= 0.80, citation accuracy = 1.00, silence accuracy >= 0.95, no sensitive
or authority-violating candidate, duplicate rate <= 0.02 and no more than 1.5
review items per acceptable proposal. Passing this gate does not authorize
production scheduling; it only permits the next shadow-evaluation decision.

## Consequences

- Quality cannot be claimed from schema conformance or a handful of attractive
  examples.
- Missing proposals and unnecessary proposals are both visible.
- A model fallback can be compared using its actual identity.
- Human review remains costly, so a small privacy-reviewed synthetic seed is
  checked in only to verify the machinery. It is not evidence of product
  quality and does not satisfy the historical/longitudinal corpus gate.
- A sanitized historical corpus requires a separate privacy review and must not
  be committed merely because an automated redactor says it is safe.
