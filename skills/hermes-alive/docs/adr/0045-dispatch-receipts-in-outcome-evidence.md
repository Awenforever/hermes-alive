# ADR-0045: Canonical dispatch receipts in outcome evidence

Status: accepted for shadow admission/read integration

## Decision

Generic delivery/task outcome admission now requires the authenticated
dispatch verifier from ADR-0044. A same-user receipt-shaped event is not enough.
Cached outcome reads and dependent reflection evidence also recheck the
original signed chain, not just its previous projection result.

Expose a shared `evidence_valid_for` predicate: user outcomes use explicit
attribution; transport/task outcomes require a start/result chain over the
exact attempt, idempotency key, capability, route/policy metadata and generation.
Source event type must agree with the claimed outcome, and the outcome must
cite its original observation in causal order. A missing existing identity key
fails closed rather than creating a replacement key during a read.

Reflection and preference consumers bind cached outcome IDs/kinds to the
original journal event, preventing a cache row from relabeling a transport
result as explicit user feedback. Valid receipt evidence does not establish
user benefit or authorize another action.

## Evidence

Replace old unsigned positive fixtures in outcome, reflection and exploration
tests with full signed synthetic host receipts built over their real
authorization/attempt fixtures. The authenticated recovery regression remains
the independent compatibility check of the canonical dispatch flow.

A regression rejects a newly submitted unsigned success observation and then
inserts it directly into the legacy cache. Current reads still exclude it;
its journal evidence remains. Valid signed outcomes and recovery, reflection,
preference and exposure behavior continue to pass.

## Limits

These tests are synthetic contract/upgrade proof, not actual user-channel
delivery. The caller still supplies a validated attempt. Receipt verification
proves start-to-result causal timing; host-clock skew and evaluation cutoff
audits remain distinct before longitudinal qualification. Operational
delivery/outcome duplication, remaining projection integrity, live host ingress
and cross-platform production matrices remain open. Production is unchanged.

On 2026-10-12 outcome, recovery, reflection, preference and exploration
regressions passed on Windows and in a disposable production-image container
with networking disabled and no production-data mounts. The gateway retained
its original start timestamp; no production update or restart was performed.
