# Phase E Interest Learning V1.1 Hardening

Markers:

- `INTEREST_LEARNING_ATTRIBUTION_V1`
- `INTEREST_LEARNING_TAG_BOUNDARY_V1`
- `INTEREST_LEARNING_DELIVERY_EVIDENCE_V1`
- `INTEREST_LEARNING_LOG_BOUND_V1`

Scope: `hermes-alive-v2-dev` only.

Hardening rules:

1. Short Latin topic tokens use word boundaries, so `AI` does not match `train`.
2. Generic questions such as “为什么” are not content feedback.
3. Weak feedback requires a recently delivered content item.
4. Generic strong feedback also requires a recently delivered content item.
5. Explicit topic feedback such as “别推汽车” updates the named topic without penalizing an unrelated source or content type.
6. Content enters `content_seen.jsonl` only when successfully sent messages contain evidence of that item.
7. JSONL logs are bounded to prevent unlimited growth.
