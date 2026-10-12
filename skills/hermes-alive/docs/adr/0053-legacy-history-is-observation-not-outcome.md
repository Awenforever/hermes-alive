# ADR-0053: Legacy history is observation, not outcome authority

Status: accepted for content-free offline baseline collection

## Decision

Export legacy log observations through an explicit scalar allowlist, outside
the public repository. Do not import them as canonical kernel outcomes or give
them synthetic authorization/attempt/receipt chains. A `sent` decision is a
legacy report, not a signed delivery receipt, useful result or user acceptance.
Every factual outcome label remains unknown.

Keep aware timestamps (normalized to UTC), pseudonymous watcher/tick/model/
decision relationships, known decision classes and strictly typed operational
flags/counts/ages. Exclude arbitrary strings, nested payloads, bodies, previews,
addresses, URLs, source tags, error/reason prose and existing unsalted hashes.
Unknown decision strings retain an opaque grouping reference, not their text.
Pseudonyms use per-export HMAC keys which are never saved. Corpus IDs distinguish
separate captures; callers must not merge locally identical record IDs across
corpora as if they were the same evidence.

Read a bounded file-descriptor snapshot. Report observed concurrent append and
invalid lines; reject detected truncation, repeated input files, oversized
sources/cohorts and output overwrite. Input order is source/line order, not
proof of causal or global event order. A snapshot reference is not a signed
source receipt, independently verifiable content commitment or reward label.

The optional SSH/container path runs the same standard-library read-only
extractor via stdin. It receives no gateway hooks, model configuration or API
credentials. Only sanitized observations leave that environment; raw source
logs are not copied locally. Never fall back to raw-log transfer on failure.

## Evidence and limits

Local tests cover content/hash exclusion, strict booleans/counts, oversized
integer ages, invalid/naive timestamps, unknown decision values, unknown labels,
domain-separated and per-export identities, malformed lines, size bounds,
duplicate sources, concurrent append/truncation and exclusive output creation.
They also check that remote POSIX paths survive a Windows caller and that the
remote command does not receive the local output destination.

A real production-image read-only export on 2026-10-12 produced 1,731 structural
records, no invalid lines, 1,731 aware timestamps and no timestamp regressions
in captured source order. Four rows carried the legacy `sent` label. All outcome
labels remained unknown. Unknown decisions formed four opaque groups. The
sample is stored privately outside Git with restricted file permissions; only
aggregate evidence is documented. Two intermediate development samples were
removed, leaving the final capture. No gateway restart or configuration change.

This is a pilot from the current log, not a qualification-sized historical
corpus, model-quality evaluation, user-feedback collection or new-policy replay.
Rotated-history coverage, retention/erasure procedures for offline datasets,
semantic source material under explicit content policy, human calibration and
actual shadow decision reconstruction remain open. Missing causal context must
not be invented to make the replay evaluator accept these observations.
