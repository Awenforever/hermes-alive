# ADR 0177: fit the generation task budget without weakening completion evidence

Date: 2026-10-18. Status: implemented; qualification in progress.

## Evidence and decision

An actual isolated current-Core run completes a long generation response but wraps
the requested JSON in explanatory text and a code fence. Existing single-shot
correction then reaches visible text with `length`, followed by `stop`. Core's
stitched final text does not equal the unique final native response. Reject it;
do not promote a parseable fragment or wrapper-stripped interpretation into exact
completion evidence. This is not a provider403 or a qualified silence decision.

Generation can return four bounded plans, dimension reasons, drafts and non-action
assessments, and the provider allowance can include reasoning. Repeated actual
truncation demonstrates that4000 tokens is not a reasonable ceiling for this
task. Use8192, the existing admitted native-worker maximum. Both initial generation
and the single correction use it within the original overall deadline. Request
count, response size, plan bounds, source/owner checks, completion evidence and
authority remain unchanged. No model-specific exception, provider configuration,
fallback registry or extra repair layer is introduced. A higher ceiling is not a
completion guarantee; fail explicitly if still incomplete.

## Existing host structured facade: measured but not yet admitted

Current qualified Core548e66f provides PluginContext `ctx.llm` structured methods,
with host-owned trust, routing, auth and fallback. Prefer existing host capabilities
over inventing a parallel API, but qualify their actual result contract first.

A network-disabled actual-Core/SDK probe replaces only physical HTTP with synthetic
responses. Default plugin trust denies model override before HTTP; the asynchronous
held transport propagates cancellation. However, the public structured result
parses valid JSON with `finish_reason=length` and with `content_filter` as ordinary
JSON results, without exposing that finish marker. Duplicate-key and fenced output
also parse permissively. A broken truncated JSON returns text, not a guaranteed
failure. Parsing success is therefore not complete-generation evidence. Alive's
strict JSON and exact completion checks must not be replaced by `result.parsed`.

The probe's configured synthetic primary403 does not produce a successful fallback,
even with an explicit backup endpoint. This only leaves that facade path unqualified;
it does not establish a defect in the production model configuration or justify
changing the user's fallback. Profile/owner revocation and physical cancellation
for other transports remain unqualified too. No Core or production file is edited,
no real credentials or network provider are used in this probe, and the facade is
constructed through actual PluginContext, not a bypassed trust-policy test factory.

## Qualification boundaries

Controlled protocol tests assert8192 on initial and corrective generation, while
retaining timeout, withdrawal, cancellation, no-respend, encrypted-artifact and
no-authority behavior. Same-public-batch live follow-up is a fix diagnostic, not a
fresh acceptance round. Keep its real terminal result, including failures or
manual quality objections, rather than resampling until a plausible message appears.

ADR0176's completed canonical regression is cb76d9e/treefc0eb58d:65 retained logs,
source554/repository577, exact archive permissions. Its synthetic contrasts do not
prove intelligence improvement over the previous criterion;7/8 predeclared outcomes
match, with the unfamiliar synthetic event uncertain. Actual final-message value,
production embedding, long-lived personalization and the original ten fresh full
clean rounds remain open. No deploy, send or restart is implied by this work.
