# ADR0274 — Compile the source citation contract before authoring

Date: 2026-10-29 (Asia/Shanghai).
Status: candidate; not production or sharing-quality acceptance.

## Evidence and responsibility

A real discovery message retained the correct primary PDF URL but displayed it
as a long bare address. Both existing authoring prompts already requested a
descriptive Markdown link. Repeating that instruction is not a repair. URL
identity and a readable, clickable citation are different properties.

Another investigation initially attributed a main-agent reading failure to
unhelpful plugin errors. The original Core tool output contradicted that theory:
Core reported the missing reference and returned its parameter schema before
invoking the plugin. The proposed duplicate argument-error mechanism was withdrawn.
Core web-extract footers in retained data and main-agent overinterpretation remain
separate issues; this change does not claim to solve them.

## Decision

New recipient-authored operations record `canonical_source_inline_v2`. The host
compiles a neutral Markdown citation from the original canonical URL into the
required source-link atom before authoring. The protected literal remains the
exact URL. The author can choose a natural label and placement; the host does
not rewrite the returned prose, shorten the URL or invent another destination.

A bounded, IO-free CommonMark parse checks that the bound primary source is a
real labelled link. Bare addresses, autolinks that still display the address,
escaped or broken markup, code examples and image syntax do not establish that
property. Other URL literals, for example a useful code sample, are not themselves
citations and are not globally prohibited or rewritten. Other facts,
overall prose quality, secondary sources, channel rendering and delivery remain
outside this check. Use the [Markdown token stream](https://markdown-it-py.readthedocs.io/en/latest/using.html)
instead of a hand-written URL or bracket-matching regex.

Candidate resolution enforces this authenticated meaning obligation, including
cold recovery and later authorization paths. A failed render remains encrypted
in the existing candidate record, while it cannot resolve as a usable message.
It is not replaced by deterministic prose and does not create a sending or retry
queue. No extra judge or model invocation is added. An invalid draft is a failed
quality attempt, not a successful silence or a credited acceptance round.

The parser dependency is declared for ordinary Hermes-managed installation and
CI. Missing dependencies must not silently disable the presentation boundary.
The LINK atom's text bound includes the small citation wrapper around the
already supported 4096-character destination; its protected literal bound stays
unchanged. Unrepresentable destinations are refused rather than silently changed.

## Preservation and verification

Non-recipient draft mode keeps its original presentation. Historical recipient
operations reconstruct their recorded v1 URL-only atoms and are not relabelled
by today's default. Existing reviewed or prepared wording remains immutable.

Verify real parsed syntax, maximum-size URLs, varied valid labels and reference
links, rejected originals retained without dispatch, and v1 cold replay. Then
exercise actual inherited-model authoring and ordinary Core continuation on
fresh sources. A stricter gate alone is not evidence of a useful, natural Alive;
the ten-round and whole-assistant acceptance obligations remain unchanged.
