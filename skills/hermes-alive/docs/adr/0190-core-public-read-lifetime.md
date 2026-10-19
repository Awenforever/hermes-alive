# ADR 0190: retain the physical Core public-read lifetime

Date: 2026-10-19. Status: candidate; not deployed.

## Decision

Connect the existing HostDiscoveryReader to PluginContext.dispatch_tool for
web_search/web_extract, not a new provider or credentials registry. Explicitly
approved public queries are bounded and exact; private memory cannot silently
become search text. Core still owns backend selection, secrets, SSRF, caching and
extraction. URL admission reuses Core's secret/shape validator and URL safety.
The adapter does not interpret tool output as instructions or delivery consent.

Core dispatch is synchronous, including its async-handler bridge. Run it off the
Gateway loop with propagated contextvars. Cancelling the wait cannot cancel that
thread or prove the vendor stopped. Retain a shielded task, retire the capability
on cancellation/timeout/authority change, and consume its eventual exception.
Hold the existing cross-platform profile file lock inside the physical worker
until it actually returns. Another instance/generation/process cannot start a
concurrent read under the same profile while that worker retains the lock.
No forceful thread cancellation or automatic retry is claimed. Owner/profile
authority is checked before dispatch and after settlement; late output is not
admitted after revocation. Shutdown may still need to wait for Core/vendor IO.
HostReadUncertainError propagates physical uncertainty through the existing
reader instead of being swallowed as an ordinary failed source. Its durable
operation stays started/incomplete; even eventual settlement does not fabricate
a completed evidence receipt or authorize automatic re-fetch.

Use the existing reader's durable started/completed operations and encrypted
requests/observations. Do not add another event store, queue or scheduler. An
incomplete operation still requires reconciliation, not automatic replay. This
read capability is not registered into production or automatically enabled by
model-only consent. Automatic public query planning/disclosure approval and its
integration into each autonomous cycle remain next product work.

## Evidence and remaining gates

Local synthetic tests pass physical timeout, continued pending work,
cross-instance exclusion, eventual settlement, cancellation, revocation,
unapproved-query refusal, profile mismatch and capability retirement. Actual
Core scoped-registry/encrypted-reader focus r2 passes synchronous search and
async extraction bridging, URL secret refusal, encrypted storage and replay
without additional reads. r1 failed because the controlled search handler
returned a dict, which Core's tool normalizer rejects; the fixture was corrected
to return JSON text. Preserve that failure rather than weakening Core's contract.
DNS and source handlers are controlled; this is not actual public web discovery.
Full canonical regression and real public source discovery remain pending at
writing. No real model, delivery, useful adaptation,
ten clean rounds or production readiness is established by these plumbing tests.
