# ADR-0035: Independent semantic review is evidence, not authority

Status: accepted for the shadow kernel

## Context

ADR-0034 established a lossless deterministic renderer and correctly refused
to let free generation self-certify. Its first conservative screen also
treated absence of an atom's full original sentence as rejection. That is
appropriate for deterministic output but would reject every useful
paraphrase, effectively preserving a renderer in name only.

Semantic equivalence is not reducible to token overlap. A rewrite can preserve
all words while reversing a relation, or replace every ordinary word while
preserving the claim. Dates, amounts, links, contacts, negation and uncertainty
still need deterministic literal guards, but ordinary paraphrases require a
separate semantic judgment. The renderer cannot supply that judgment itself.

## Decision

For model candidates, missing protected literals remains a hard rejection.
Changed or paraphrased ordinary atom text becomes `review_required`, not
automatically wrong. Deterministic rendering remains exact and unchanged.

Introduce a provider-neutral independent-review contract bound to:

- the exact UTF-8 candidate digest;
- the meaning event and complete atom set;
- actual renderer and reviewer model identities;
- distinct renderer/reviewer execution IDs; and
- distinct independence domains.

A model cannot review its own output, reuse the same execution, or masquerade
behind a different display name in the same declared independence domain.
Human review is represented separately and cannot claim a model identity.

The reviewer must classify every atom, added claims, speech-act preservation
and protected-literal preservation. Findings use separate risk classes for
omission, contradiction, unsupported addition, polarity, uncertainty, time,
quantity, reference and speech-act shifts. No blended similarity or "semantic
score" hides which obligation failed.

Even a complete clean review grants only `shadow_eligible`. It never grants
truth, evidence entailment, action authority, route authority or automatic
delivery. A later persistence layer must authenticate review receipts and bind
them to the latest validated selection before any canary is considered.

Add a versioned multilingual adversarial replay format and complete-cohort
scoring. Qualification reports faithful acceptance, unsafe acceptance,
per-risk recall, issue precision and independence violations separately. The
checked-in 12-case Chinese/English/Japanese seed proves evaluation machinery
only; it is explicitly marked as non-qualification evidence. Shadow
qualification requires at least 100 blinded cases, three languages, zero
unsafe acceptance, high faithful acceptance/issue precision and calibrated
human judgments.

## Consequences

- Useful paraphrase remains possible without weakening exact guards around
  high-risk literals.
- A model's confidence, JSON validity or self-critique cannot cross the trust
  boundary.
- Reviewer diversity is explicit and auditable instead of inferred from model
  aliases.
- Evaluation cannot silently omit difficult or no-error controls; the entire
  declared cohort must be scored exactly once.
- This milestone still performs no model call, persists no review receipt and
  changes no production behavior. Those integrations remain blocked on a
  larger blinded corpus and human calibration.
