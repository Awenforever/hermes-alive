# ADR-0005: Explainable memory retrieval uses ranked evidence

- Status: accepted for kernel shadow development
- Date: 2026-10-10
- Depends on: ADR-0002, ADR-0004

## Context

An Alive system needs to recall relevant experience, not merely the newest or
highest manually assigned number. A single opaque “memory score” would repeat
the old architecture's problem: relevance, importance, recency and authority
would be mixed into an uninspectable heuristic. Sending all private memories
to an external embedding or reranking service by default would also violate
the privacy boundary and provider-neutral design.

## Decision

Retrieval first applies deterministic state, validity and sensitivity filters.
Only authorized, available values are decrypted in process. It then:

1. computes lexical relevance with BM25;
2. independently ranks importance, recency and evidence authority;
3. combines rank positions using Reciprocal Rank Fusion (RRF);
4. returns the component ranks, matched terms and full memory provenance with
   every hit.

A non-empty query requires a lexical match, so a recent but unrelated memory
cannot enter merely through recency or importance. English-like text uses
normalized word tokens. CJK text uses overlapping two-character tokens (and a
single character only when the entire run has length one), avoiding the high
false-positive rate caused by common single characters.

RRF is used because the component scales are not commensurate. It avoids
inventing a claim that, for example, `0.8 importance` is directly comparable
to a BM25 score or a timestamp. The fixed RRF constant affects rank smoothing,
not semantic admission, and every component remains visible.

## Privacy and authority

- Search receives records only through `MemoryProjection.retrieve`, so both
  set search and direct lookup require explicit sensitivity clearance.
- Plaintext search text and token counts are ephemeral and never persisted.
- Erased, missing or integrity-failed content is excluded from normal search.
- A duplicate claim observed at a stricter sensitivity raises the logical
  memory to that stricter level; deduplication can never downgrade privacy.
- Authority is one ordering component, not a substitute for evidence or a
  way to auto-promote model inference.

## Semantic retrieval

This decision does not reject embeddings. It rejects silently exporting all
private memory as the default. A future semantic scorer must be a Hermes-owned
capability with explicit local/external disclosure semantics, encrypted or
erasable derived state, provider inheritance and an independently testable
fallback. BM25+RRF remains the deterministic baseline and replay oracle.

## Evidence

- Chinese research queries rank relevant memories while excluding a more
  important and newer unrelated memory.
- no-match queries return no result rather than “best available” noise;
- component ranks and matched terms explain every hit;
- private clearance cannot observe restricted records;
- forgetting removes a hit immediately;
- discard-and-rebuild reproduces durable timestamps, IDs, RRF scores and
  component ranks;
- stricter duplicate evidence switches the primary reference to matching
  higher-sensitivity ciphertext while retaining all copies for later erasure;
- the existing memory authority, provenance and erasure contracts remain
  green.
