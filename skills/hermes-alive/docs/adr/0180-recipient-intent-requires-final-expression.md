# ADR 0180: one recipient meaning, execution only after final expression

Date: 2026-10-19. Status: implemented; canonical qualification pending.

## Problem

Modern candidates carry both an illustrative draft and a communication plan.
Purpose, selection and expression use the retained plan, but factual review also
sees the draft. A measured real case has conflicting units in those two objects.
The draft is additionally stored as a typed channel contract. Normal preparation
supplies a validated final expression, but lower-level authorization historically
permits exact stored content when no expression ID is supplied. Independent
policy/route/confirmation/delegation gates still apply: no bypass or unintended
production send was demonstrated. Nevertheless, an integration must not promote
a modern internal thought to executable wording by omitting one argument.

## Decision and compatibility

New recipient-meaning interpretations pin expression-required-v1 in both the
host-owned start method and the encrypted proposal bundle. Recovery checks exact
agreement, the known mode and its required recipient-meaning binding. Unknown,
partially missing or mismatched contracts fail. Old bundles with no such mode
retain their original behavior and snapshot digests; no historical rewrite.

For these new internal intents factual assessment uses only the retained plan,
like purpose, selection and expression. The illustrative draft remains retained
provenance, never a second recipient-facing message to judge or execute. Final
source review still independently assesses the actual rendered wording. A plan
is not source evidence, calibrated utility, permission or proof of user interest.

The common current-selection validation additionally checks execution mode when
invoked by first authorization, retained-permit recovery and dispatch. New intent
without a final expression is rejected. Supplying an ID alone grants nothing:
existing exact-expression validation, current-source checks, confirmation or
delegation, route, expiry and authenticated content binding remain necessary.
Normal SendPreparationRuntime already supplies this expression. No new sender,
queue, model registry, memory store, judge or deterministic rendering is added.

## Evidence and limits

Focused tests cover conflicting draft/plan model views, no-expression rejection,
fake expression IDs, initial authorization and replay, dispatch validation,
owner isolation, mismatched modes and preserved legacy behavior. Adjacent planning,
source review, authorization, preflight and final expression suites pass after
fixing purpose review's obsolete assumption that every snapshot contains a draft.
The initial failing regression is retained, not counted as success.

A read-only copy of actual earlier experimental state reopens original and repair
completions plus reviews without inference, new events or changing historical
source windows. This does not prove production host embedding or usefulness.
The draft is still redundantly generated/retained; removing that output requires
versioned generation/recovery work rather than silently changing old contracts.

Next inspect actual new-path wording against source relationships and recipient
contribution, then complete the bounded useful loop and the full long-term
memory/agenda/feedback, physical host lifecycle, migration and ten fresh complete
clean-round requirements. This change alone earns no clean acceptance round.
Production, Core, model configuration, other plugins and wmw are unchanged.
