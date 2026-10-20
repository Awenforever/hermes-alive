# ADR0193 — Preserve the evidence already obtained by a directed deep read

Status: implemented; canonical qualification pending at writing

## Actual evidence

Fresh public Core search returned six listings and the current model selected two
pages for deeper reading. Both extracts succeeded. The retained extraction sizes
were 6353 and 2982 characters, yet synthesis and source/purpose review independently
cut each to 1800 characters. In one source, museum demonstration evidence began
at offset1958, directly relevant to the tentative reading question. The information
was obtained and stored but removed before the reasoning stage. This is an input
continuity defect, not a claim that it caused a particular final style failure.

The real experiment later stopped because its private logging wrapper replaced
the caller's route_info object. Both review responses returned but the correct
runtime provenance guard rejected missing caller-visible routing. Fix that
instrumentation, not the guard; preserve failed receipts. No final expression or
quality-round credit exists. The real generation route also showed the configured
official fallback; elapsed time alone does not establish the reason for fallback.

## Decision

Use one versioned source_prompt_excerpt boundary for synthesis and source/purpose
review. New interpretations record retained-web-extract-v1. For authenticated
host web-extract scope this carries the stored bounded extraction, up to8192
characters; ordinary listings and admitted commitments keep their existing1800
window. Collector/scope provenance is unchanged. The shared24000-character recall
budget and fair source cursor still apply, with no extra source-count/claim quota.

Review derives the policy from the original interpretation, not today's default.
Historical operations without this method field keep their original1800 scope;
this preserves data/replay semantics, not compatibility with old Hermes releases.
Unknown policy is refused. A complete stored extraction is still an excerpt,
not full-page reading, video consumption or independent verification.

## Qualification and next work

Controlled actual synthesis/review snapshots prove late evidence reaches both,
listing scope stays bounded, old/absent policy retains original behavior and
unknown modes do not silently expand scope. Existing recall-window, inquiry and
source-support tests pass with real encrypted storage and synthetic calls.
Canonical/full regression pending at this entry. Do not replay failed model
stages implicitly or count this component proof as recipient value.

Next run the corrected private recorder against a newly identified operation,
then connect the bounded discovery stage to the consented installed host. No
production deployment or send. All long-term memory, agenda/outcomes/reflection,
Halo, migration/portability, ten fresh clean complete rounds and acceptance gates
remain; this change does not by itself fix conversational judgment.
