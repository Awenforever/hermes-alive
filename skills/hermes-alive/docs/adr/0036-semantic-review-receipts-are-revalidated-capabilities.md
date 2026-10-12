# ADR-0036: Semantic review receipts are revalidated capabilities

Status: accepted for the shadow kernel

## Context

ADR-0035 defines what an independent semantic review must contain, but an
in-memory verdict is not durable evidence. Persisting only the word "passed"
would be worse: a later intent could supersede the selected message, encrypted
content could be forgotten, the meaning could expire, or a receipt could be
replayed against different model output.

Append-only history also creates a subtle trap. An event can remain authentic
as historical evidence while no longer being valid authority for current use.
Signature verification alone cannot distinguish those states.

## Decision

Persist free model render candidates in the erasable encrypted content vault.
The journal stores only a content reference, SHA-256 candidate digest,
structural atom-change metadata, exact validated selection, actual renderer
model/execution, declared independence domain and explicit authority nonclaims.

Persist an independent review as an installation-authenticated structural
receipt bound to the exact candidate event. The receipt records complete
per-atom findings, reviewer kind/model/execution/domain, added-claim and
speech-act checks, disposition and separate risk classes. It stores no review
prose and grants no automatic-delivery authority.

Every consumption revalidates the full dependency chain rather than trusting
the stored disposition:

1. authenticate the candidate and review event payloads;
2. decrypt and hash the exact candidate text;
3. resolve the encrypted meaning and deterministic protected-literal screen;
4. prove the same candidate remains the latest validated selection;
5. reconstruct and rerun the independent-review assessment; and
6. enforce causal order and the current expiry boundary.

Erased candidate or meaning content, a newer validated selection, changed
renderer evidence, invalid reviewer independence, tampering, future-dated
consumption or expiry makes the current receipt unusable. The historical event
is retained as history; it is not silently rewritten or deleted.

The API accepts an explicit `as_of` for deterministic replay tests. Normal
consumption uses current UTC time, so an expired receipt cannot become valid
merely because its event was created before expiry.

## Consequences

- Review evidence survives restart without turning append-only history into
  permanent authority.
- Privacy erasure has operational force: once ciphertext is erased, dependent
  candidates and review receipts fail closed.
- Model attribution and independence can be audited without storing private
  candidate text in the journal.
- A clean receipt is still shadow evidence only. Provider invocation,
  qualification-corpus calibration, user correction and delivery canary
  remain separate unfinished milestones.
