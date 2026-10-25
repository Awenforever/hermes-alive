# ADR0236 — Core-scoped retained-reference reader

2026-10-26, Codex. Status: candidate; actual Core tool-dispatch qualification pending.

## Why

ADR0235 keeps a normal exact share intact but cannot fit a longer reference into
an arbitrarily smaller host hook budget. A file-path placeholder is not sufficient:
the actual public-only main agent did not possess a file-read tool. Source bundles
can also exhaust the older store view's aggregate budget before the newest outward
text reaches the final projection. Preserving history is not proof that an agent
can retrieve it.

## Contract

Use Core PluginContext.register_tool for alive_read_reference, in a scoped toolset
and the normal tracked lifecycle. No arbitrary file paths, network calls, separate
memory service, provider selection, sends, transcript writes or renewed permits.
Current conversation text is selected before optional source excerpts. A compact
opaque handle remains when exact text cannot fit the hook; normal complete text
still goes directly into context.

Handles are minted only after the existing main-turn scope gate. They name one
retained share, one canonical Core conversation and one Core task. They live in a
bounded64-entry process-local map for at most600seconds; repeated projection does
not extend a handle. Core supplies task/session IDs to the registry handler;
model arguments cannot select them. The handler requires task-local gateway
binding, matching owner/profile/receiving account/thread/session, live generation
and original retention/forgetting checks. Foreign scope is refused before body
decryption. Replacement/unload retires handles. No ambient/default conversation
fallback exists.

The tool returns bounded pages of exact text or one retained source excerpt,
with offset/next_offset/total/complete and actual reported reading scope. Pages
are fragments, not a complete document or fact-verification verdict. No page
extends retention, infers delivery, imports an interest, learns feedback or creates
execution authority. Core owns whether its toolset is enabled; do not broaden a
user's configured tool permissions to make this reader available.

This first boundary covers current-session retained references. Searching older
quoted topics, cross-session recall with correct consent and ordinary daily memory
remain required work; do not present them as implemented by a new tool name.

## Qualification

Exercise actual Core registry and hook dispatch on encrypted authorized fixtures,
including a whole share larger than the hook cap and multi-page source/text reads.
Keep default/invalid/tiny/disabled host cap checks, exact whole text, scoped cold
reattachment and no protected-history changes. Refuse wrong task/session/profile,
unknown/expired handle, source or subject forgetting, replay after replacement and
unloaded generation. Validate real Core main-tool calling before claiming natural
long-reference continuation; a direct synthetic handler call is insufficient.
## r88 observed contract failure

The first actual Core registry test refused a dict result from the new handler:
"handler returned unsupported result type: dict". No scope refusal or provider
failure was involved. Keep r88 and its diagnostic immutable. The next candidate
serializes the outer tool result to JSON text, as Core's dispatch contract requires;
internal reader values stay structured. No qualification is claimed for r88.

The r89 actual collector test passes its ordinary cases, then rejects the oversized
synthetic fixture at the existing12000-character channel-action boundary. The
next fixture is above the10000-character hook cap and below the original12000
channel cap. The action contract and retention limits stay unchanged; do not
weaken a delivery limit merely to exercise history paging.

r90 passes five focused suites with the actual Core registry and collector,
including the long authorized-share fixture, exact multi-page reconstruction,
source pages, task/session refusals, handle expiry and deletion. No real model or
production is involved in that component proof. The next compact notice also
preserves the original reference-only/non-delivery and related-topic boundaries
when the full contextual header itself cannot fit. Actual main-tool selection
and API input/result verification remain pending; no quality round is credited.

## Actual Core main-tool qualification and evidence kinds

The actual supported Core defers plugin tools behind its own tool_search /
tool_describe / tool_call surface. Keep that mechanism; do not disable it or grant
broader tools merely to satisfy a direct-tool-only harness assertion. The first
two private preflights made no model requests and failed that assertion. A c run
then completed two real official-model turns with two exact reader results, but
the old final whitelist still rejected Core's discovery observer. Its failure is
preserved. Corrected d is TERMINAL0: initial512-character context lacks the share,
the model discovers/calls the reader, later actual requests contain the full
prepared wording, the second contains the first real reply, sends0 and original
kernel journal sequence unchanged. Credentials audited before removal. It is a
same-source control, not a fresh quality round or production-default proof.

The answers still overgeneralize a layer-dependent observation. Do not patch
that paper's wording or claim that a later self-correction repairs the first.
The tool contract must also distinguish its resource types: recovering a prepared
share is not independently reading its cited page. Return a host-derived content
kind and a bounded title/URL/scope catalog with source indices, so an agent can
request actual retained excerpts rather than guessing an index or treating its
own prior message as verified primary evidence. Catalog entries contain no
excerpt; this is explicit. No statement that this fixes general model reasoning
is justified. Final typed-catalog component and actual-main tests remain pending.

## Typed-reader qualification, 2026-10-26

r92 passes the five-suite actual Core focus. Its real official-model same-source
control is TERMINAL0: no original share text in initial512-character context,
Core's own deferred discovery, two complete prepared-text reads plus one real
source-excerpt read, two completed consecutive main turns, actual prior reply in
the second request, sends0, no native loop and original kernel sequence unchanged.
The real results contain the host-derived content kind and three-entry source
catalog. Credentials audited before removal. This qualifies the current-session
API and model use, not semantic accuracy or a fresh quality round. The first
answer still overgeneralizes a task/layer-dependent result; the second makes an
unsupported claim about an unreported experiment. Do not add paper-specific rules.

The next fixture also checks Core's actual platform toolset resolver: defaults
admit a newly registered reader on CLI/Telegram/Weixin/Feishu; a known saved
suppression or global disabled_toolsets remains authoritative. This is not an
SDK connection or four-device distribution claim. Cross-session/old-quote recall,
ordinary memory and final Git/fleet/production acceptance remain open.

r93's actual collector/default-resolver checks pass. The final candidate also
refuses expired or absent source excerpts instead of returning complete=true with
an empty successful payload. Separately retained outward text remains readable,
and its catalog explicitly reports that a source is no longer retained. This
failure-path change preserves original scopes, TTLs, payloads and tool permissions.
It requires its own actual Core expiry test; prior real-model qualification is
for r92's retained-source path, not a claim that this new branch has run in a model.

## Superseding the experimental handle clock, 2026-10-26

The initial600-second handle timer above is superseded before publication.
A read handle carries no independent authority: every use already requires the
live Core task/session/owner/generation and original retained content. A separate
10-minute timer could break a legitimate slow multi-step model task without a
permission change, especially with100-second provider responses. Keep the64-entry
process-local bound and retire handles on replacement/unload; validate original
retention and forgetting on every read. Do not invent a shorter read delegation
or renew an original data/send authorization.

The final fixture checks a still-authorized Core task after a synthetic hour,
refusal of expired original data before decryption, and retired handles after
reattachment. Automatic default context still refuses other sessions; this change
adds neither cross-session access nor an external-memory provider. r94 is an
immutable intermediate build without a completed focus; the final candidate
requires new Core qualification. Real-model retained-source proof remains r92;
its outputs are not general reasoning or fresh-source quality proof.

## Final scoped-reader qualification, 2026-10-26

r95's five actual Core focus suites pass, including expired source refusal,
original retained-data expiry before decryption, replacement retirement,
default platform toolset resolution and explicit suppression. r96 differs only
in internal documentation/manifests: exact runtime and test bytes/modes match
across460 files. Its full99 portable regression passes, terminal0. Committed
r96 tree de8bcd4cd820c350ab15c0304538fd78adc6f28d, commit0cd9555.
The candidate retains the original privacy/authority contracts. No production,
external delivery or fleet claim follows from these component results.

The preceding model-semantic verdicts require calibration: independent inspection
of the versioned primary preprint found attention-mask experiments and support
for the frame-count efficiency trend. See the memorandum's evaluation-calibration
entry. A model's later self-criticism must not establish absence of experiments,
and faithful plain-language explanation is not automatically a new empirical
claim. Original physical missing-context failures remain unchanged. Old-source
controls still do not qualify fresh content quality.
