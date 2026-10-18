# ADR 0174: host reads into the existing discovery journal

Date: 2026-10-18. Status: implemented; full canonical regression passed.

Terminal regression: commit 7067b59, canonical tree e363f0e, 65 retained logs;
source/repository manifests and exact archive permissions pass. This uses the
existing managed dependency environment, not fresh-dependency qualification.

## Decision

HostDiscoveryReader accepts explicit owner-bound search/extract/safe-URL/current
capabilities from Hermes. It does not select providers, discover credentials or
private profiles, infer interests, schedule work or send messages. Queries must
already be approved for external disclosure. Autonomous query planning and a
production-owned physically cancellable read lease remain embedding work, not
capabilities proved by callback presence or a CLI test.

Reuse DiscoveryOpportunityIngestor and its authenticated entity/material versions.
Search listings and webpage extracts have separate stable observation scopes;
a later listing cannot overwrite a deeper page read. Retrieval time belongs in
observed_at, not volatile content attributes. Identical retained tool content does
not become a new version merely because collection runs later. Byte changes in
tool output are not proof of a meaningful world event or recipient novelty.

Requests are retained in the existing encrypted vault, not plaintext event fields.
Durable started/completed records retain bounded observations, read outcomes and
failure counts, without provider errors or execution grants. Reopening a completed
operation revalidates owner/current sources and does not repeat reads. An incomplete
operation is not restarted; cancellation/uncertainty retires that instance until
host reconciliation. URL safety and physical IO lifetime remain host-owned. Storage
failures propagate; they are not disguised as ordinary source unavailability.

Known empty search results differ from failed/unknown results. Extra optional
provider fields are ignored; finite JSON, bounded items and required content/URL
types remain checked. Unreadable/invalid sources do not erase independent valid
observations or the general discovery pool. No publication date is invented from
the query or collection date. Existing expiry/withdrawal rules are not bypassed.

Pass collector-reported read scope to both interpretation and source review.
Page extraction is not watching a video or independently verifying its claims;
page navigation, other items and tool notices are not all current-article facts.
Legacy sources without the new scope keep their prior snapshot representation.
Reported attributes cannot promote themselves to proof of verification or viewing.

## Measured qualification

- Initial standalone focus ab06aa3 fails because the fixture imported before
  establishing its temporary Hermes home. Corrected fixture 0a4218f passes; no
  plaintext-storage fallback or host dependency change is made. Local Python lacks
  cryptography; encrypted tests use the existing isolated managed interpreter.
- Focused runtime/test trees 33390ee and 118116d pass owner/replay/version/general
  preservation, missing/error/unsafe data, revocation, cancellation, privacy and
  adjacent interpretation/source/selection tests. Extended focus a7fe1c0 also
  passes concurrent-read, stale replay, storage-failure and finite JSON cases.
- Actual current-Core CLI integration performs one search plus two original reads,
  producing five observations; an independent general-science query adds three.
  Reopening repeats no reads. This uses public sources, empty web profile, no
  projected web credentials, model call, private chat or transport. The CLI runs
  in an externally time-bounded owned container; it is not a production daemon
  cancellation/lifecycle qualification. Later fixture/observation-time refinements
  are covered by final regression, not retroactively called exact live-tree tests.
- Actual owner r5 uses those eight retained observations and explicit consented
  interests: generation and source/purpose reviews complete, then both selector
  attempts truncate. Diagnostics show length with visible partial text, followed
  by stop; exact completion rejects Core's stitched text. Failed trials remain.
- Selector's 500-token ceiling is below a reasonable combined reasoning/output
  allowance. Match other cognition stages at a bounded 4000 tokens, leaving Core
  routing/reasoning/fallback and exact-completion checks unchanged. This is not a
  guarantee for every model or acceptance of fragments. Controlled tests assert
  the ceiling. A retained-frame diagnostic r6 then completes one real Qwen call
  and selects share without redoing collection, interpretation or reviews.
- Retained-expression r7 fails before inference from a diagnostic harness using
  the wrong vault/store construction, not lost data or provider failure. Correct
  construction r8 renders with Qwen and receives official DeepSeek semantic/final
  reviews (shadow_eligible/supported), with no dispatch/authorization/send.

## Product result is still incomplete

Manual review rejects the r8 message as a press-release-like inventory with too
many statistics/features, despite model approvals. Some source relationships and
ambiguous comparison/date scope need more care; no new factual precision should
be invented by combining adjacent source sentences. No clean round is claimed.

Editorial selection belongs before meaning becomes immutable, not in a renderer
silently deleting approved facts. Clarify that discretionary shares choose a
substantive recipient-relevant angle, not exhaustive source compression; preserve
material qualifications and requested detail. This is a general prompt correction,
not a phrase blacklist or an independently validated naturalness fix. It needs
fresh, substantive held-out evaluation rather than repeating the same release.

Full integrated runtime, autonomous/noise-resistant personalization, external
memory, long-term agenda/feedback, migration/forgetting, lifecycle qualification,
ten fresh complete clean rounds and production acceptance remain open. FIFO stays
with the channel enhancement. Production, wmw and other plugins are unchanged.
