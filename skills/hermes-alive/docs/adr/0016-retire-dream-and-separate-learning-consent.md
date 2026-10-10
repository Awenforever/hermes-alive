# ADR-0016: Retire Dream and separate learning consent

Status: accepted for the shadow kernel

## Context

The legacy Dream implementation was described as non-destructive and
operator-reviewed, but source inspection found a different contract. It read
raw session transcripts and could apply model-produced operations directly to
`MEMORY.md`, the fact store and voice state. That bypassed the new per-user
content-retention boundary and confused model confidence with authority.

Retaining content and learning from content are also different grants. A user
may want encrypted, expiring history for continuity without allowing a model to
derive persistent claims from it.

## Decision

The legacy Dream engine is retired, not repaired. Its public class remains only
as an inert compatibility tombstone: it never becomes due, never reads a
transcript, never calls a model and never mutates memory, facts or voice. The
lifecycle rejects attempts to enable it.

The replacement consolidation path requires both:

1. explicit per-user retention consent for the relevant inbound or outbound
   content; and
2. separate explicit per-user learning consent through Hermes' authorized
   `/memory alive learn on` command path.

Both grants default off. A consolidation candidate must cite one to 32 durable
conversation events for exactly the same subject. Every event must reference
currently decryptable, authorized retained content. Erased, expired, missing,
structural-only and cross-subject evidence fails closed.

Model candidates are restricted to expiring `fact`, `preference` and
`self_model` hypotheses. They cannot create commitments, request deletion,
supersede a record, change consent or activate themselves. Candidate prose is
encrypted in the content vault; structural history stores provenance, a keyed
content digest, model identifier, expiry and the review-required disposition.

Every admitted model candidate enters typed memory as `proposed`. Activation
requires a self-authorized `/memory alive accept <id>` event. The same command
surface supports rejection and later retraction. A forged model event, another
subject or a reused ID with changed semantics is rejected. Projection rebuild
must reproduce consent and review state.

## Consequences

- A stale environment variable cannot silently revive unsafe Dream behavior.
- Content retention does not imply interpretation, and learning consent does
  not create evidence that was never retained.
- Model output remains useful for synthesis while staying below the authority
  boundary.
- The user can inspect pending proposals and explicitly accept, reject, retract
  or erase them.
- Candidate generation is a shadow primitive only. Scheduling it or consuming
  accepted memories in live decisions requires separate evaluation and a later
  production gate.
