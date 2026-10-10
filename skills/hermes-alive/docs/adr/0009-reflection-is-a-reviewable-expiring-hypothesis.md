# ADR-0009: Reflection is a reviewable, expiring hypothesis

- Status: accepted for kernel shadow development
- Date: 2026-10-10
- Depends on: ADR-0002, ADR-0008

## Context

An agent that cannot consolidate experience remains shallow. An agent that lets
its model directly rewrite long-term preferences after one interaction becomes
unstable and self-confirming. Delivery receipts, ordinary replies and missing
replies are particularly weak evidence of user benefit.

## Decision

A reflection is a typed hypothesis, not memory truth and not a behavior rule.
It contains encrypted hypothesis text, predicted implications and limitations;
structural metadata records its scope, confidence, expiry, model/authority and
the exact observed outcomes used as evidence.

Only explicit feedback, correction, dismissal, or repeated downstream task
outcomes may support a model reflection. Delivery success and ordinary replies
are excluded. Non-explicit task evidence must span at least two independent
action attempts. Every model reflection expires within a bounded horizon.

All reflections begin as `proposed`. Acceptance or rejection requires a
matching inbound user event. An accepted reflection can later be retracted by
the user. Acceptance still does not mutate typed memory or policy; promotion is
a separate, attributable operation.

## Consequences

- A single successful send cannot become a learned preference.
- A model cannot approve its own generalization.
- Expiry limits stale self-narratives and concept drift.
- Review and rollback remain possible after restart or model replacement.
- Erasing private prose preserves only its structural digest and review history.

The initial projection is shadow-only and has no effect on production behavior.
