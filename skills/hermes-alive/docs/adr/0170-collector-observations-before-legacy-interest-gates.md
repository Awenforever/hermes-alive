# ADR0170 — Preserve observations before legacy interest and sharing gates

Date: 2026-10-18. Status: implemented in isolation, qualification in progress.

## Evidence

ADR0168 fixed admission of already ingested sources. Inspecting actual upstream
collection now exposes an earlier gate: DiscoveryEngine applied heuristic interest
ranking, a share threshold, delivery-topic suppression and editorial budgets before
the kernel shadow saw anything. A useful or unfamiliar observation could disappear
before model judgment. A new actual-engine regression initially fails because no
independent observation reader exists. This is an acquisition/admission problem,
not an invitation to increase a permanent top-N interest score or add a judge.

One actual isolated external run obtains 18 observations from NASA's public RSS,
Bilibili listings and Sspai's RSS; the old sharing pipeline retains only 12.
V2EX times out but the old generic health reports ok=true/fetched=0. A second
run under the new request instrumentation obtains eight domestic observations,
records NASA connection failure and V2EX timeout as failures, and continues both
available domestic sources. No private profile terms, model calls or sends are
part of these collector runs. They demonstrate bounded live behavior, not stable
availability, full-video/article reading or recipient accessibility.

## Decision and boundaries

Keep a separate, in-memory collector snapshot before legacy mutations/filters.
It contains external observations and source health, never local discovery.
Round-robin by collector plus declared publisher/feed identity before a 128-item
capacity bound; collector popularity and learned interests do not decide admission.
Keep fetch time and omitted count, return deep copies, and require freshness.
Do not expose the snapshot as another field in the legacy composer context.

Only the opt-in kernel discovery shadow reads this snapshot. Missing/stale data
does not silently fall back to the semantically different gated sharing list.
It admits up to the snapshot capacity through the existing private encrypted
ingestor. The legacy ranking, reservation guards, compose input, send decisions,
model configuration and all channel transport ownership remain unchanged.
Observation is never approval, dislike, send authorization or proof of delivery.

Track HTTP failures and exceptions inside the shared async request boundary under
task-local collector context, including failures safely swallowed by a collector.
Health retains bounded error classes/status codes, not request URLs or exception
messages. Partial results remain usable but are marked partial/ok=false. Empty
results without observed request errors are empty_or_unverified/ok=null, not an
assertion that the source worked. This is request health, not proof that all
payload parsing, semantic extraction or publisher claims are correct. Existing
collector logs are not replaced by this metadata mechanism.

The observation adapter now preserves timezone-qualified RSS/RFC publication dates
as well as ISO dates. Unparseable/timezone-less values remain unknown and retain
their raw value in protected attributes; never assign the collection time as an
invented publication instant. Model interpretation explicitly treats interests as
soft preferences while respecting actual exclusions and avoiding random filler.

## Verification and non-claims

The new regression collects 141 synthetic observations, while the simulated
legacy pipeline mutates/discards all candidates. The separate 128-item snapshot
preserves the original data and the low-hint second feed, reports 13 omitted,
does not contain local data, resists caller mutation, and actually ingests 128
private kernel observations through the watcher boundary. No actions or dispatches
appear. Stale/missing snapshots do not call ingestion. Controlled real collector
responses exercise timeout, HTTP503, partial RSS and unknown empty status across
parallel tasks, plus date retention and proxy override behavior.

Five focused isolated suites pass. The first broader run passes four but exposes
an older proxy test relying on a synchronous tuple rather than an async HTTP
context; that test now enters the real context and also verifies an explicit
proxy override. The updated five-suite run passes. Local full-boundary testing
cannot pass without the required cryptography dependency; no plaintext workaround
was added. Complete current-tree portable CI is still pending at this record.

Native public-material interest contrast r1 uses the same 18 live observations
and synthetic, non-owner profiles. Qwen3.8 completes baseline abstention, then a
worker call fails before returning a completion. Keep that failure; it does not
prove a provider outage or a successful profile contrast. The probe now preserves
bounded worker diagnostics and saves attempted-call counts before awaiting work.
The separately bounded interest-only follow-up terminates after one actual logical
attempt with NativeCompletionError at completion: diagnostics show one API start,
no observed terminal API event, no completed/failed/partial/interrupted result flag,
and no exact completion-coordinate match. A returned final string alone is not a
native completion. No candidate is admitted. These diagnostics do not establish
the underlying provider status or justify weakening completion validation. Do not
keep retrying this pool or label it a successful profile comparison. Both cases
end with no pending workers, actions, authorization, dispatch or send; projections
are removed after worker/container termination.

The capacity limit is not exhaustive coverage or durable pagination of an
arbitrarily large feed. Overflow within one publisher can remain unseen; capacity
must not be described as semantic rejection. Profile-directed network queries,
qualified chat-noise extraction, external-memory integration, genuine longitudinal
feedback, complete expression quality, ten fresh clean full-chain rounds and
production/distribution acceptance remain open. The ADR0169 first-person evidence
attribution failure is not fixed by this admission change. No production/wmw/Core/
other-plugin edit, restart or real message is part of this work.
