# ADR 0115 — Explicit bounded permission for natural expression

Date: 2026-10-14

## Decision

Extend the trusted user-command grant API with literal boolean
`allow_natural_expression`, default False. Only explicit True adds a signed field
to a new grant. Historical grants and new default grants retain their existing
payload and scope: upgrading must never silently permit model rewording.
String/numeric truthiness is not permission. No production grant is created here.

The send-time authorizer accepts the exact current expression either through
existing exact user confirmation or through a current USER_DELEGATED grant that
explicitly covers natural expression. The latter still checks owner, current
policy, destination binding, share/ask kind, sensitivity, expiry and revocation.
Model review does not create or expand this grant. Exact expression resolution,
selected-source provenance and contract binding are unchanged.

Replayed permits, outbox route qualification and the transactional cadence/start
boundary all request the natural-expression permission when an expression is
present. Revoking after preparation blocks start; revoking after internal start
blocks the qualified launch check. Existing interval and rolling-day budgets
remain enforced on consumed starts, not guessed user benefit or delivery.

This closes the API-level per-message-confirmation restriction recorded in
ADR-0114, but not the whole autonomy milestone. The actual authenticated user
onboarding/control path must explicitly obtain and explain this scope. It must
not infer acceptance from plugin installation, an old grant, a generic reply or
positive model review. Independent expression/source assessments remain quality
evidence, not permission or calibrated truth proofs.

## Evidence

Windows new runtime test passes historical-grant refusal, explicit-grant exact
expression preparation/start, revocation before start, revocation after start
before launch, and malformed permission rejection before journaling. Existing
delegation and authorizer regressions also pass.

Isolated Linux `alive-expression-delegation-offline-20261014-r1` exits 0 for the
new five-case test, send-preparation regression and the full existing opportunity
execution suite. `alive-expression-delegation-regression-20261014-r1` exits 0 for
delegation, authorizer and dispatch-cadence regressions. Both have network disabled,
read-only scratch mounts and 1 CPU/2 GiB/256 PIDs. Models, grants, routes and user
identity are synthetic. Internal starts in the tests are not external launches.
No private chat, real model call, external send, production restart/configuration
change or wechat-enhance edit occurred.

Dependency snapshot is ADR-0114's unchanged r2 source plus these exact files:

- authorizer SHA-256: `6db0ea9a8b602680b1efb62c8fea7fb8ff301863d5f0940788213e7cf1479c2a`
- delegation SHA-256: `c2bea09f608e0ab2289efee89cc386b8e06f71f1d0d37bd35f7879f18987c3e6`
- outbox SHA-256: `d527c34d5a9e6182d327a723b81f95f067a65adcda10ae79046de277ae5c5866`
- expression store SHA-256: `03e60189b1e0857ac6f09d8e78f0f2fa6596b21d59333189f475e69a9f09814a`
- new test SHA-256: `f2fcedcf02217ccd00b077a3ab08a35c8363215b90eacf27e5a63360a5608494`

Next: compose the actual qualified Hermes transport, attributable delivery and
feedback, bounded scheduler activation and authenticated onboarding. Validate
real-model natural expression on new public/synthetic scenarios and longitudinal
utility. Preserve full portable install/upgrade/rollback and production acceptance;
do not declare success from API permission or these controlled model fixtures.
