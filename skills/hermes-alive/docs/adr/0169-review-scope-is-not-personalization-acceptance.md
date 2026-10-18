# ADR0169 — Review scope is not authorization or personalization acceptance

Date: 2026-10-18. Status: experimental, not deployed, semantic qualification failed.

## Observed behavior and narrow decision

An independent review of a retained synthetic/public draft correctly questioned
unsupported directory structure and first-person verification, but also objected
to missing sending permission. A repair was then factually questioned mainly
because it had no delivery grant. Fact support, recipient purpose and execution
authorization are different decisions. Internal consideration must not require
authorization to send; factual support must never grant it.

The experimental source and purpose contracts now identify their limited scopes.
The snapshot explicitly says execution authorization is not evaluated, no sending
was performed, and a reported source is not an execution receipt. A claimed action
or permission still requires evidence. No dispatcher, permission, action history,
queue or model configuration was changed. Changed snapshots deliberately invalidate
old review eligibility; historical evidence is not rewritten for cache reuse.

The probes now retain native completion diagnostics and allow explicit isolated
per-role host-model projections. A controlled replay checks a prior completion's
fingerprint and candidate identity before comparing a new reviewer. Replayed
generation is labeled, not counted as fresh inference or a fresh clean round.

## Actual results, including contradictory evidence

The retained-review r1–r5 series made seven logical attempts including one worker
failure without a completion. One repair emitted invalid JSON then used the bounded
model correction path; neither original failure was erased. A controlled replay
of the valid repaired candidate passed the new fact-support scope. However, the
original ambiguous draft also received a supported verdict under that scope.
This is not a successful negative control or proof that actor attribution works.

A separate composed expression case made seven actual model calls: configured
DeepSeek generation/selection/expression and Qwen3.8-reasoner review. Source,
purpose and final-source reviews returned supported; semantic expression was
shadow-eligible, not authorized. Reopen required no inference. Manual inspection
still found the final message saying in Chinese that the assistant had verified
directory availability and entries, while the evidence was an operator collection
note. This is a semantic failure even if it resembles the collector's true action.
It is not a clean full-chain acceptance round. The text also needs a separate
recipient-value review rather than ever-longer procedural caveats.

All cases used synthetic ownership and public evidence. Each terminal report
records zero action attempts, dispatches and sends, and no pending workers.
Temporary model exports were removed by the wrappers; production configuration,
private chats, other plugins and wmw were not changed. Physical HTTP attempt totals
were not instrumented; logical attempts must not be presented as that total.

Four adjacent isolated suites pass: source support, commitment cognition,
source-support history and final wording preparation. Complete current-tree CI
is still pending. A suite pass and cross-family agreement do not supersede the
manual semantic failure or count toward the required ten fresh clean rounds.

## Next bounded milestone

Do not respond by banning a verification phrase, adding another judge, or
repeatedly sampling the same directory example until it passes. Preserve the
failed example as a holdout and inspect how collection actor/evidence scope is
represented through planning and expression. Qualification must include a clear
unsupported-action negative control and a supported reported-source control.

More importantly, return to the integrated product milestone: private explicit
profile, relevant accessible discovery (including domestic content), model value
judgment and attributed feedback over time. The owner's complaint is uninteresting
production recommendations, not a request for an indefinitely expanding reviewer
framework. PERSONALIZATION_DELIVERY_PLAN.md specifies implementation order,
anti-noise memory boundaries, China-accessible source policy and finite acceptance.
No new infrastructure or production deployment follows from this ADR.
