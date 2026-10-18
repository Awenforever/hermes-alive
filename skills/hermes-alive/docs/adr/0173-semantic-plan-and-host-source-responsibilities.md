# ADR 0173: semantic meaning and host-owned source binding

Date: 2026-10-18. Status: implemented; full isolated regression pending.

## Failure and responsibility

A real, consented isolated profile trial completed native generation, but every
proposed communication plan was rejected: link atoms contained labels while their
protected URL occurred only in protected_literals; other atoms paired translated
prose with absent original-language literal phrases. These were genuine contract
errors. Do not silently insert absent text, discard literal validation, reinterpret
old accepted plans or treat all-malformed proposals as qualified silence.

The existing host already binds canonical source evidence before selection and
adds a separate protected source-link atom during expression. Asking a model to
duplicate that URL across draft/plan/protection fields creates unnecessary failure
opportunities. Semantic prose and exact-character protection are different duties.

## Decision

Expose the existing source presentation policy in the trusted stage_contract.
For canonical_source_v1, tell the model explicitly that the host owns the canonical
link. Focus its plan on meaningful content; a redundant canonical URL atom is not
required. Other meaningful links still require the actual URL in their own content
and literal protection. Translated semantic facts need not protect absent original
phrases. Exact amounts/dates/addresses/identifiers, where needed, must occur in
the content that protects them. No validator, source binding or execution authority
is relaxed. No post-acceptance rewriting or new review layer is introduced.

Clarify that an unlisted topic is not negative interest evidence, and a matching
topic is not automatically valuable. This is not an exploration quota or proof of
longitudinal diversity; explicit exclusions still bind the system.

## Evidence and remaining work

- Focused suite passes on runtime/test tree 19fad51: semantic plans without a
  redundant link retain the host's exact canonical link, including a long URL;
  selected frame and original plan remain unchanged; reopening requires no new
  inference. Neutral fixtures retain rejection of absent URLs/literal phrases.
  Existing bounded JSON-recovery, expiry/owner/context and legacy binding tests pass.
- Actual private-profile r4 exercises that tree with 24 public observations, Qwen
  interpretation/selection and official DeepSeek source/purpose review. One valid
  candidate passes both reviews; selection chooses silence for insufficient value
  from the available abstract-level evidence. Four logical calls complete and
  replay without inference. No expression/final-source review/send occurs. This is
  not a useful delivered sample or a fresh full-chain clean acceptance round.
- Final code adds an explicit conditional wording for noncanonical presentation
  policies after that trial; real model r4 is evidence for the focused wording,
  not an exact-prompt qualification of every later edit. Do not rerun the same pool
  merely to manufacture a message or count another clean round.
- An empty-profile actual Hermes web_search_tool capability test returns relevant
  domestic video/history results with no projected service credentials/model call.
  Some results are old: topic relevance, publication time, original-read depth,
  user accessibility and novelty are separate. Search endpoint success is not
  personalized discovery integration or verified news/video understanding.
- Next improve actual discovery substance through existing host search/extraction,
  with source dates/attribution and bounded profile-directed plus general material.
  Do not force sharing, weaken source evidence, add topic-specific patches or
  substitute safe silence/model approval for the owner's usefulness assessment.

Initial canonical CI tree 828e4ae fails the base synthesis fixture's exact
stage_contract assertion, which did not include the newly declared source policy.
Update its exact expected contract without removing authority/owner/privacy
assertions; retain that failed run. Full corrected CI and final-tree manifest
validation remain pending at this writing.
Production is unchanged. Memory/noise, sustained feedback/agenda, forgetting and
migration, lifecycle/release, ten fresh full-chain rounds and production acceptance
remain required under the full living plan.
