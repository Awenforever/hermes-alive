# ADR 0256 — Attention deferral and owned execution authority

Status: implemented; isolated qualification in progress, not production acceptance.
Date: 2026-10-27.

## Problem

ADR0242 defines snooze as a change to follow-up availability, not delegated
work authority. Actual Core case r211 showed an already admitted file job losing
its effects after a fresh owner snooze. The initial-work pre-tool guard used the
same future-availability/latest-transition test as selection of new work.
Even snooze followed by resume changed that version permanently.

## Decision

Keep latest item versions for owner commands, model snapshots and result closure.
Keep availability gates for initial work, new inspection and outcome selection.
An existing producer or already admitted inspector instead validates its original
signed item version against the currently authenticated agenda chain. Only an
unbroken run of active/snoozed transitions in the same task lifetime qualifies.
Never cross completion, cancellation, expiry or reopening. Configuration, original
source, expiry, owner policy, job definition, exact Core execution, tool scope and
stop fences still apply. No new authorization, executor, retry, source inference
or automatic replacement job is introduced.

This also permits result assessment after an attention-only resume, while its
admission and effect remain bound to the latest exact transition. An earlier
assessment cannot close a subsequently reopened item. New inspection must not
attach an old producer to a reopened lifetime merely because the wording matches.

## Evidence boundaries

- r211 retains the failing actual-Core attention-snooze counterexample.
- r213 actual Core snooze and snooze/resume cases pass: the admitted job performs
  its actual write/read, no additional job or outbound message.
- r214 actual Core cancellation, cancel/reopen, assessment after attention resume,
  stale-result refusal after reopening, pre-tool pause and assessment-time pause
  pass. The prior inspector qualification also passes on the new runtime.
- r215 admits an inspector, snoozes attention before its actual read, resumes
  attention and consumes the fresh observation. Cold identity/association checks
  pass without adding another job or broadening the approved read target.
- Whole portable regression r214 is still in progress; no final claim is made.
- This is synthetic controlled-provider Core integration, not fresh real-model
  interpretation, physical process sandboxing or production/fleet acceptance.
