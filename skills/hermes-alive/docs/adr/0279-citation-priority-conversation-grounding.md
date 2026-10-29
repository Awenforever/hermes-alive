# ADR 0279 — Budget conversation evidence around the actual share

Date: 2026-10-29. Status: candidate; qualification pending.

## Evidence

An isolated inherited-model trial reached two ordinary Core followups. Both
requests included the exact share and 3453 characters from an older background
article, but omitted the excerpt from the article the share actually cited.
The retained source was available; greedy collection-order packing spent the
context budget on the background first. Main-agent overinterpretation remains a
separate semantic failure, not something this packing repair guarantees to fix.

Subsequent size inspection found that the actual cited body is 11409 characters:
it cannot fit whole in the existing 10000-character hook budget even alone.
Priority fixes starvation when an excerpt fits; the existing scoped read tool
must handle larger evidence. Do not claim priority alone fixes this real case.

## Decision

Keep exact outward wording and existing latest-share priority. Within admitted
shares, reserve source catalogs before allocating whole excerpts. Give actual
labelled Markdown citations first choice of catalog and excerpt space. Use the
existing CommonMark citation parser, without topic, publisher or model rules.
Keep output catalogs in collection order and include their original zero-based
`source_index`, including when an earlier source cannot fit. That index addresses
the existing scoped `alive_read_reference` tool; it grants no new access.
The existing reference instructions explicitly require reading an omitted source
before making claims dependent on it, or acknowledging unavailability. This is
ordinary evidence retrieval, not a new review/model stage or a reading guarantee.

Keep whole serialized units under Core's existing hook budget. An excerpt too
large for that budget remains explicitly absent, with its retained-reading scope
and original tool index where metadata fits. Do not truncate, summarize, increase
the global budget, make extra model/network calls, or misrepresent an excerpt as
a full source. Unbounded/already-fitting context is unchanged. Protected records,
retention, erasure, consent, route ownership and read-tool validation are unchanged.

## Qualification

Reproduce background-first starvation against the preceding implementation, then
cover both collection orders, reference-style citations, catalog pressure,
unchanged source indices, exact text, whole excerpts and serialization bounds.
Run the existing actual-Core continuity/retention/route controls before adoption.
These checks do not establish natural conversation, factual judgment, real
delivery, fleet compatibility or production acceptance.
