# ADR 0278 — Admit source content independently of optional display titles

Date: 2026-10-29. Status: bounded controlled qualification; broader acceptance pending.

## Evidence and decision

A real Core extraction returned a useful model-card body but an empty title.
The host boundary rejected it because the display title was mandatory. A local
regression reproduces that failure before this change. This is a source-contract
problem, independent of the topic, website, extraction provider or model family.

Keep mandatory evidence checks separate from optional presentation metadata.
The exact requested URL, host URL permission, owner binding, body type/size,
request count and physical-read settlement retain their existing checks. An
extraction still needs nonblank text. An untitled search listing also needs
nonblank text; an existing title-only listing remains admissible.

A supplied nonblank title of at most 512 characters keeps its previous exact
representation. Otherwise use the explicit label `Untitled public resource`,
with `title_is_placeholder=true`. Source provenance passed to interpretation,
authoring and review marks `source_title_available=false`; the label is not a
claimed headline. Do not invent titles, infer authors/dates, manufacture a
summary, make another network/model call, or silently truncate an overlong body.
Unusable optional title metadata is not retained as source text.

The encrypted observation format and existing title-required internal candidate
remain unchanged. Named historical evidence keeps its existing representation.
Completed failed reads are not silently retried under new semantics: a fresh
read is a distinct operation. A placeholder grants no new source authority,
interest inference, delivery permission or retention exception.

## Qualification

Cover absent/null/blank/unusable optional titles with unchanged usable bodies,
named and title-only legacy listings, refusal of URL-only/empty/oversized/wrongly
typed bodies, substituted or private URLs, current owner binding, read-once
recovery and erasure. The actual current Core depth fixture supplies untitled
extracts through its ordinary registry and asserts that missing-title provenance
reaches interpretation and authoring before a local adapter submission.

These checks do not prove extraction quality, factual correctness, useful
recommendations, natural conversation, fleet or production acceptance.

The new host regression failed against the preceding runtime at its first
untitled extraction, then passed after the boundary change. The frozen candidate
also passed host discovery, public-source refinement, excerpt scope and retained
source-support controls. Its current installed Core fixture completed every
controlled model stage, retained the missing-title provenance through source
interpretation and authoring, and submitted once to the local test adapter.
Both 6000- and 15000-character extraction windows were exercised. No real model
or external message was used; native Git-consumer and broad qualification of this
specific delta remain separate gates.
