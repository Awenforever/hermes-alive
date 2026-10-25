# ADR0232 — Query-dependent search views are distinct evidence

2026-10-25, Codex. Status: candidate; actual regression and full qualification
pending. This does not authorize release, production, private reads or delivery.

## Observed failure

The actual r79 archaeology chain read a substantive article, then performed its
one approved additional public search. That response included the same article
with a different snippet. The ingestion identity was source plus canonical URL,
so the new query's snippet superseded the original listing. The original reading
question still correctly depended on that listing. Its current-source check then
raised DiscoveryInquiryError and stopped the cycle before further reading or
writing. The retained sequence directly shows the replacement followed by failure;
this was not a model-quality refusal or proof of a storage failure.

## Decision

Treat query plus canonical URL as the identity of a search view. Use a digest as
the existing candidate external identity; keep the actual original URL and source
text unchanged. Different query snippets can coexist. Material changes within
the same query view still supersede earlier versions, and real page extracts keep
their existing identity. No source-currentness, erasure, owner or expiry check is
relaxed. This is evidence identity, not factual verification or a preference.

Within a query response, keep the first successfully admitted result for a
canonical URL. Duplicate tracking variants do not create successive revisions in
one batch. Do not merge snippets or substitute normalized URLs as fetch authority.
Refined reading excludes already attempted canonical URLs, preserving the one
bounded followup budget without unnecessarily rereading the same page.

New configured cycles declare the identity mode durably before the initial
search. A started cycle without that marker keeps its original request and
identity rules. No stored observation is rewritten, renewed or resurrected. The
direct host-reader embedding keeps the old default unless explicitly selected.
The flag is not consent for a new query: the existing disclosure grant is still
required before every physical call.

## Required evidence

Test overlapping and entirely repeated results through the actual durable
reader, inquiry and final research-group resolver. Test changed material within
one query, erasure, legacy replay, duplicate URL variants and no extra I/O on
replay. Run actual Core integration and the portable suite, then repeat the real
public-source chain and inspect the original share and consecutive main turns.
A safe stop, successful source read or exit0 is not a useful quality round.

## Integration finding before acceptance

r81's actual installed-Core wait check failed: the new per-cycle mode event
changed the general owner frontier even when the semantic listing fingerprint
was unchanged, spending inference again. The refinement mode had the same
integration omission. Include those two control events in the existing bounded
listing-wait exemption. Their mode values are already part of the authenticated
listing fingerprint; changed source content, owner context, unknown events,
inbound input and expiry still wake it. Exercise the actual native wrapper both
with ordinary reads and separately opted-in refinement. Preserve r81 as failed
evidence and qualify a new immutable candidate.
