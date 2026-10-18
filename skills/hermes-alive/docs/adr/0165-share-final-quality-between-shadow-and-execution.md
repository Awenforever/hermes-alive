# ADR0165 — Share final-evidence quality between shadow and executable cognition

Date: 2026-10-17
Status: implemented and isolated-tested; full acceptance remains open

## Problem

ExpressionRuntime qualifies wording against a retained meaning plan. It cannot
alone establish that the final wording is supported by the original evidence.
SendPreparationRuntime already performed that separate final-source review and
bounded correction, but the non-executing AutonomousCycleRuntime path bypassed
it. Shadow success therefore exercised a narrower pipeline than the executable
path, precisely where actual wording can change actor or verification claims.

## Decision

SendPreparationRuntime.assess exposes the existing final quality/correction
composition without requiring or manufacturing a route, user confirmation,
delegation, send permit or action attempt. It returns ExpressionQualityResult,
not an authorization. Cancellation propagates; unavailable repair is attention,
not successful silence or permission to reuse rejected wording. Repair-disabled
quality does not itself demand confirmation; only prepare maps that state to
requires_new_confirmation for an actual immutable confirmed-message contract.

prepare retains its original route preflight before model spending and now
reuses assess, then independently evaluates execution authority. No channel IO
or FIFO responsibility moves into Alive. Confirmed wording is not automatically
rewritten. Both paths use the exact same final-source review receipts and bounded
repair lineage; no second quality implementation or deterministic fallback body.

AutonomousCycleRuntime shadow mode now invokes assess. Grounded results carry
a quality_assessment, while prepared/submission remain absent. Rejected or
unresolved quality yields content_review_attention, never shadow_selected or
silence. Ungrounded selection behavior remains, with quality_assessment=None. Owner
policy, current model capability and host lifetime remain separate requirements.
Explicit host model_timeout_seconds also reaches this final source-review call;
it cannot widen the independent owned process lifetime.

## Verification

The new shadow-final-quality test invokes actual AutonomousCycleRuntime with
synthetic model outputs, no route and an authorizer spy that forbids evaluation.
It exercises supported quality, unsupported quality with unavailable correction,
and unavailable review. Reopen is inference-forbidden and separately counts any
callback attempts so caught AssertionError cannot manufacture a replay pass.
It checks canonical action.attempted/action.authorization_evaluated events and
absence of external dispatch. Seven adjacent shadow/send-preparation/final-repair/
host/expression/commitment entries pass offline under installed Hermes. These
are composition contracts, not genuine model/transport or semantic-quality proof.

The native public-expression probe supports resuming an exact completed public
synthetic-owner journal. It validates the original report's owner/evidence and
completed status before reading credentials, then copies rather than edits it.
Case native-public-expression-real-20261017-r3 resumes r2 and adds the previously
missing final-source stage. Actual qwen3.8-reasoner/custom:ustc returns supported
after one new logical invocation; exact reopened assessment spends no inference,
pending_workers0, attempts/authorization evaluations/dispatch/sends all0. The
case is terminal, its --rm container absent and temporary credential projection
removed and verified absent. r2's six earlier model calls are not repeated.

The phrase claiming 'I verified' remains a manual actor-attribution concern
despite this model approval. Do not relabel it a certified error-free round.
Next qualify who-observed/who-acted semantics using adversarial contrasts and
original evidence, rather than a first-person keyword ban or another renderer
patch. Broader fresh scenarios, longitudinal learning/agenda, memory/Halo,
forgetting, migration/rollback, installation and production acceptance remain.

Regression entry points are wired into both run_all.sh and the actual portable
CI script. CI requirements now explicitly include cryptography50.0.0, matching
the existing plugin.yaml contract, instead of assuming an ambient installation.
This is not a claim that fresh dependency resolution, latest Core compatibility
or the entire CI suite has already passed. Current official Core has a newer
50.0.1 pin; reconciling and testing that dependency policy remains a lifecycle
qualification task before release, not permission to modify production Python.
