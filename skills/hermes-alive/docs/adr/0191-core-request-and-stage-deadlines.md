# ADR 0191: separate Core request timeouts from Alive stage deadlines

Date: 2026-10-19. Status: candidate; not deployed.

## Measured problem

The adapter forwarded the same timeout to Core's request and its own outer wait.
Actual Core, real SDK with controlled HTTP and no network reproduces the bug:
task request timeout0.04s is overridden to3s, and the outer3s timer cancels the
primary before Core can recover. Only the primary is observed. This does not
prove the cause of prior real-model/native-worker timeouts or model availability.

## Decision

The callable timeout now means a finite whole-stage deadline only. Pass None
through Core's facade request-timeout field so Core retains the effective task
timeout, candidate-specific timeout, retries, routing and fallback decisions.
Do not implement a parallel provider ladder or edit primary/backup model settings.
Keep the explicit total cap600s; omitted stage timeout uses that cap rather than
reusing the old90s request-sized default. Explicit shorter total deadlines remain
real limits and can legitimately preempt recovery; no fallback is guaranteed in
insufficient time or outage. This is not permission to repeat the logical stage.

The opt-in shadow task's operational request default is180s, with explicit600s
stage budgets forwarded across generation, source/purpose review and semantic
render/review. Actual owner evidence includes successful92–99s calls; the initial
candidate60s default was rejected before release rather than treating its499s as
model unavailability. Core can ordinarily fit two180s primary windows and a180s
fallback inside600s, with finite headroom. Existing Core auxiliary
user configuration and per-fallback timeouts still win. This is a bounded initial
default, not evidence of optimal latency for all models or a promise that every
possible ladder completes. Slow/reasoning task budgets belong in Hermes config.
No production configuration was written or experimental kernel activated.

Default actual product validation uses the current Hermes primary/fallback.
Different-family models are optional diagnostics, never a dependency or a
replacement for the owner's primary test path. No owner model identifiers,
credentials or interest presets enter public defaults.

## Evidence and remaining scope

Local caller unit passes, including overall timeout, authority change, override
denial and incomplete native response refusal. New assertion ensures no stage
timeout is forwarded as Core request override. Actual Core controlled fixed
focus observes primary0.04s, its Core retry0.04s, backup0.2s, and complete native
backup response, with correct separate credentials. This is inheritance and
recovery evidence, not real inference, independent review, useful content or a
fresh quality round. Initial Core probe fixture dependency warnings persist;
this is the retained managed environment, not fresh dependency qualification.

The first short-stage probe incorrectly required an HTTP start; corrected test
accepts cancellation during cold initialization, and passes with zero HTTP. This
is total-deadline evidence, not physical cancellation of every provider. The
first candidate full regression passed, but its60s policy is superseded and is
not acceptance of the revised budget. Revised canonical regression is pending.
Generic403 classification, other API modes and
physical cancellation of all wrapped/synchronous providers remain open. Do not
replace strict finish metadata, infer dislike from timeouts, or turn this budget
fix into another model-selection project. Return to useful source-guided depth,
natural actual messages, attributed feedback and the complete memory/agenda/
outcome/forgetting/migration/lifecycle/production acceptance objective.
