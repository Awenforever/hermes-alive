# ADR0235 — Budget conversation references before Core hook spilling

2026-10-26, Codex. Status: candidate; projection boundary passed on Windows,
actual Core collector and same-public-share main continuation pending.

## Evidence

The actual r85 VLM native run inherited the configured Hermes main/fallback.
USTC returned successful responses and timed out twice; Core-owned official
DeepSeek fallback succeeded. The native cycle made one local adapter submission
and settled its work. The first actual main turn completed, but its physical API
requests lacked the exact submitted share. This was a genuine integration failure,
not evidence that a prepared share was never saved or that the model was unavailable.

The Core turn collector spilled a10,341-character hook result above its10,000
character default. Its500-character head and tail contained general instructions
and source figures, but lost the exact share. The bounded public-only main agent
could search again but had no file-read tool for Core's private spill path. Its
answer inferred an unsupported length/benefit trend. The probe correctly failed;
there was no real channel send, no successful dialogue or quality-round credit.

## Decision

Keep the authenticated journal/vault reference unchanged. At the Core-facing
boundary read the active profile's hook-spill settings through load_config_readonly,
using the supported Core constants/coercion. Never disable spill, raise its limit,
write configuration, inject fake transcript history, grant file access or alter
model routing. Disabled spill still respects the store's bounded context ceiling.

Measure the actual serialized hook output. Preserve complete most-recent outward
words first, then earlier complete shares, whole citation/scope descriptors and
whole source excerpts as space permits. No source clause, URL, negation, prepared
text or JSON document is cut to fit. An omitted excerpt is labeled as absent from
this request; it is not unavailable research or proof of a negative world fact.
If the latest complete reference cannot fit, never silently present an older one
as the current topic: report the missing reference when the budget can fit that
notice, otherwise return no context and emit a non-sensitive warning.

This repairs the demonstrated normal-share handoff. A deliberately smaller cap
than the whole outward text cannot carry that exact text; transparent omission is
not seamless long-reference retrieval. Scope-safe bounded recall for that case,
old quoted topics and production conversation continuity remain open requirements.
No second memory service or transport queue is introduced.

## Required qualification

Use the actual Core collector and its real spill implementation under default,
custom, string, invalid, tiny and disabled limits. Demonstrate intact prepared text,
whole source units, unchanged protected trace/configuration/messages, cold reattach,
foreign scope refusal, expiry and forgetting. Replay the settled public reference
into real consecutive main turns without rerunning its source search/composition,
then inspect exact physical model inputs and original answers. Correct delivery
alone does not prove semantic correctness, recipient value or fleet acceptance.
## Actual qualification, 2026-10-26

r86 /6c14c61 passes five focused suites, including actual Core plugin scan,
guided setup/control and the expanded collector tests. Windows atomic projection
checks pass. The first two private replay harnesses failed before inference
because they registered the test adapter's Core factory too late; their original
inputs and terminal failures remain. A new corrected c harness registers the
factory before connecting, restores the original authenticated routing identity,
reattaches the old encrypted kernel and starts no native task.

Its two actual consecutive official DeepSeek main replies receive the complete
original r85 share in physical requests, without a spill preview. Prior actual
reply is preserved; no send or kernel-journal change occurs. No public source or
authorship is rerun. Credentials were audited before removal. This qualifies the
context handoff, not the model's assertions: it still converted "not only the
visual encoder" into "not the visual encoder" and claimed an abstract-page read
that its later reply contradicted. Quality remains0/10; no production-default,
fresh-source, external-delivery, old-quote or fleet acceptance is claimed.
