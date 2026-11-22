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

## 2026-10-29 — Bounded qualification update

The regression failed against the preceding runtime, then passed the candidate.
The current installed Core passed source controls, continuity across success,
failure, consent/route/retention changes, budget limits and reference-tool reads,
plus the untitled/deeper-reading chain and one local adapter submission. The
combined candidate passed the complete portable CI, with its reduced stress
configuration explicitly retained as a test limit.

An existing inactive Ubuntu consumer upgraded through normal Git installation
and runtime refresh. All 35 logical state/key fingerprints remained unchanged;
packing, current Core continuity and complete source-depth controls passed from
the actual installed tree and Core-managed interpreter/dependencies. Core and
plugin working trees remain clean; no prefixed worker remains. There were no
real models or external sends in these qualification controls. A prior isolated
real trial identified the omission, but no new real main-agent continuation has
yet qualified this repair. Whole-platform, active-job, daemon, fresh semantic
quality and production gates remain open.

Clarification of the earlier unchanged-context statement: complete share/source
representation is unchanged when it fits. The reference-tool instruction header
also gains the explicit omitted-excerpt reading instruction in those contexts.

## Distinguish the share from its background material

In the actual archaeology replay, a successful second read supplied the link
used in the share. In ordinary follow-up, the model gave the background index
as the link that had been shared, even though the index was marked uncited.
The exact wording and Markdown destinations remain the record of what the
share says. The context and reference tool catalog now expose the retained
sources matching those destinations apart from the other material. The original
source index remains the address for paged reads. A source may help answer a
question regardless of which group it belongs to. If a comparison's method or
baseline is absent, the ordinary turn should leave it unresolved.

The groups describe the model-facing projection. Stored receipts, clearances,
refusal rules and Core ownership of the ordinary reply are unaffected.
Controlled packing and reference reads establish projection behavior. Repeat
the same factual questions on actual Core and verify with fresh cases before
crediting conversational quality.

## Core can replay older hook text

The isolated supercomputing trial recorded the exact requests for three
ordinary turns. Core included each earlier Alive augmentation in the
conversation prefix as well as the current augmentation. The third turn
presented a page read from the second as though it had just performed it.
The request and tool receipts show that no new read occurred in the third
turn. The trial also failed separate explicit brevity requirements.

Core 0.23.3 stamps user-row `api_content` for prompt-cache replay. A
network-disabled control replayed a synthetic marker from the historical
sidecar with an empty current hook response. The original user text lacked
the marker. Thus omitting an Alive reference now and stopping replay of
already-materialized context are two different operations.

Qualify this boundary before production. A Core-owned mechanism must
distinguish ordinary message content from plugin-supplied transient evidence
and handle expiry, erasure and revalidation on new turns, including after a
restart. Investigate whether a supported host mechanism suffices. Track
reference-tool results and actual visible chat history separately. The plugin
should never seize the profile's single context engine or rewrite ordinary
messages to simulate erasure. A future reference-only mode would still need
to account for material returned through tools and retained by Core.

## Qualify request-time reference resolution

Core 0.23.3 exposes the public `llm_request` middleware after provider
payload construction. A prototype writes an opaque reference into the Core
API-facing user row, then resolves it at request time. The prototype binds
the reference to the current session, task and turn. When the record cannot
be revalidated, the request contains only the inert reference. The ordinary
message text and previous replies retain their normal Core history.

A controlled run passed with a current grant and refused on withdrawal,
expiry, a different session, a later turn and middleware retirement. A
separate real-model run used an actual synthetic Alive share, opened an
erasure event, and made a second ordinary Core request with the same
history. The first request contained the authorized material. The second
contained neither that material nor the private test marker while both
stored user rows retained their exact ordinary text and opaque references.
Only Chat Completions was exercised end to end.

Real Core transport conversion retained the synthetic context and tool
markers across Chat Completions, Anthropic Messages, Bedrock Converse and
Responses. The carrier differs for each, especially for tool outputs. This
establishes usable locations, not a complete provider matrix. Before
adoption, qualify output sanitization after request middleware, retry and
fallback reconstruction, path-specific tool results, owner and profile
binding, and cold resume. Historical plaintext from older releases remains
a separate migration concern. Provider retention, visible prior replies,
and user-authorized exports remain independently governed.

The development candidate uses this pattern for the share context hook.
Only a bounded reference and its admission envelope are kept in memory.
An exact current-session, current-task and current-turn marker resolves
against the current store and router. Duplicate markers, unmatched scope,
unknown carriers and retired registrations leave only the inert marker.
Sibling hook text can remain alongside a marker. This implementation
does not yet protect previously stored plaintext or change how Core
retains agenda text or feedback context.

For the reference tool, Core histories keep an opaque receipt rather
than the retained page. The actual model request resolves it for the
same session, task, turn and tool call. Offset, source index, and the
original research scope are revalidated when rereading the vault.
The supported carriers are Chat Completions tool text, Anthropic
tool-result text, Bedrock tool-result text, and Responses function
output. A stale receipt remains inert even when Core keeps it among
ordinary tool history. Content previously materialized by older
versions and independently retained assistant replies have their own
migration and withdrawal requirements.
