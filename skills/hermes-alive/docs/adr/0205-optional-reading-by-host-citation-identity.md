# ADR0205 — Optional reading by host citation identity

Date: 2026-10-23 (Asia/Shanghai). Status: implemented, qualification pending.

## Evidence and gap

A real installed shadow cycle supplied two useful original extracts. Its optional
follow-up selected a verbatim HTML link and a project URL whose PDF text attached
a sentence period. The model omitted that period; the old lexical boundary
rejected the URL and aborted the complete cycle. This was not a completely
invented resource. Existing initial evidence and the other valid target were
unnecessarily lost before comprehension/authorship.

Do not fix this by stripping punctuation or adding characters to an allowlist.
Core currently supplies extracted text, not an independent hyperlink table. It
cannot prove whether punctuation belongs to a URI. Model copying followed by
whole-decision rejection is the wrong representation and fault boundary.

## Decision

For newly recorded cycles, freeze `cited-public-followup-v2` before the search.
The host enumerates at most 32 conservative URI spans per current extract with
source-scoped identifiers, exact offsets and unchanged original URL text. It
does not repair, percent-decode, normalize, expand relative URLs or infer targets.
Parenthesized framing is balanced; ambiguous bare/incomplete framing is unavailable
rather than a newly fabricated truncated endpoint. Sentence punctuation stays in
the span. These are textual references, not verified hyperlinks or certificates.
An ambiguous URL may fail its actual read; that failure remains unknown evidence.

The model chooses up to two `(source_ref, citation_ref)` pairs or abstains. The
host resolves IDs against that exact table. Canonical identity is used only for
already-read/duplicate resource exclusion, never to alter a fetch URL or bypass
Core URL/DNS/SSRF/secret checks. The existing reader still verifies the exact URL
returned by the tool and records individual read failures.

Selection validation is candidate-local: unknown/foreign IDs, extra URL fields
and duplicates are rejected and counted; valid siblings remain eligible. An
unusable structure or non-JSON optional response is recorded as an invalid
decision, distinct from intentional abstention. It grants no new read and does
not discard initial evidence. This is not a deterministic model fallback, a
fabricated model decision or a reason to call another model. Core still owns
provider routing/fallback. Missing model attribution, actual provider exceptions,
cancelled or uncertain physical work, revoked consent, changed owner memory and
withdrawn sources remain genuine failures, never swallowed as optional errors.

The existing encrypted choice completion records accepted IDs, a tentative
reason, rejection count and selected/invalid/abstained status. Reopen validates
those IDs against the original bound sources, not a fresh search. Expanded raw
URLs are a transient host projection, not model-authored targets. No new store,
scheduler, delivery queue, judge or provider configuration is introduced.

## Upgrade/recovery

An existing search start without the new pre-search mode marker remains v1.
Its original prompt, choices, failures and exact matching are unchanged; do not
reopen a failed historical operation with the new parser or repeat inference.
New operations may use v2; completed v2 choices reopen without inference, while
incomplete choices remain reconciliation-required. Erasure and current source/
owner/consent checks remain authoritative before and after selection.

## Proof obligations

- Exact URI spans, punctuation preservation, balanced framing, bounds, exclusion
  of credentialed URLs and already-read resources; no endpoint truncation.
- Mixed valid/invalid choices preserve only the valid targets. Invalid structure,
  non-JSON and foreign IDs never create a fetch or erase initial comprehension.
- Deliberate abstention remains distinguishable from rejected choices.
- Real installed Core composition, old-v1 replay, new-v2 no-inference reopen,
  consent withdrawal, source erasure, physical interruption and profile privacy.
- Full regression and new real-provider material validation, with complete output
  inspected. Controlled IO passing does not prove natural sharing quality.

This addresses optional acquisition robustness only. Persistent inquiry follow-up,
useful learning, external memory, ten fresh complete quality rounds, four-platform
distribution and final production acceptance remain open.
