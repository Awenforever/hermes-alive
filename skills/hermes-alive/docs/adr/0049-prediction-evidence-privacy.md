# ADR-0049: Prediction evidence has an owner, clearance and lifetime

Status: accepted for shadow evaluation

## Decision

Evidence must be available before prediction generation, within the supplied
privacy clearance, in the attempt subject's scope and unexpired at generation.
The only unscoped exception is a PUBLIC event with no subject. Public-tagged
events belonging to another user are not implicitly shared; unscoped private
events are not global context. Unknown sharing authority fails closed.

Historical evaluation checks expiry at prediction generation, not at today's
clock: a legitimate old prediction remains inspectable, while a prediction
that used already-expired evidence cannot qualify. This validation reads only
journal metadata and never decrypts a cited evidence payload to enforce scope.

## Evidence

The real admitted evaluation fixture includes earlier own-private, foreign
private/public, own-restricted, unscoped-public/private and expired events.
Regression rejects foreign ownership, excess clearance, unscoped private data
and expired evidence while accepting own-scope and truly global-public evidence.
Existing future-evidence and factual-label provenance checks remain active.

On 2026-10-12 the full Windows kernel suite reported 35 passed, one official
hook test skipped for absent Hermes runtime and zero failed. The missing hook
test was then run with the real HookRegistry/PluginManager in an isolated
production-image container, alongside evaluation/outcome regressions: all
three passed. Networking was disabled; only test source was mounted read-only.
The runtime emitted a missing `tzdata>=2025.2` dependency warning. This is not
a clean-install dependency qualification; retain that warning as a separate
Phase 6 issue rather than hiding it behind the passing hook result.

## Limits

This is an evaluation boundary, not a new sharing/consent mechanism or a proof
that a model was genuinely trained only on declared data. Remaining projection
integrity, receipt duplication and human/live qualification remain open.
Production is not modified.
