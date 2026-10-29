# ADR 0277 — Bound SQLite resource lifetime to one native operation

Date: 2026-10-29. Status: bounded controlled qualification; broader acceptance pending.

## Evidence

The installed Git consumer reached final launch on an actual native Ubuntu VM,
but its prepared message expired before the adapter call. The same controlled
pipeline passed in a tmpfs-backed container. An actual profile identified about
127,000 SQLite executions, 6,393 content resolutions and thousands of connection
closes in one model-free test cycle. Repeated source recovery and store creation
amplify local IO. This is a product performance/readiness failure, not permission
to widen the execution deadline or skip a freshness check.

## Hypothesis

Closing the last WAL connection after every nested query repeatedly checkpoints
and tears down database resources. Keep one idle connection per accessed database
for the duration of a native step, while all ordinary short-lived connections
continue executing exactly the same reads, writes, authenticated source checks
and access audits. Measure the native result before adopting broader changes.

The operation scope stores resources, not query results, decoded content,
authorization decisions or a retained read snapshot. Its keepers execute only a
completed metadata read and hold no transaction or cursor. Independent writers
and erasure remain visible to every ordinary query. Existing WAL, synchronous
and secure-delete settings are unchanged; backups still require the documented
SQLite/WAL-safe procedure.

Nested scopes share one resource owner. Inherited thread context may use it while
active, but cannot reopen resources after retirement. Connections are not reused
across processes. At most sixteen keepers are retained; unsupported URI/locking
cases retain ordinary connection behavior with a diagnostic. URI `mode=rw`
prevents a keeper from recreating a concurrently removed file.

Exit, failure and cancellation close all keepers. A scope does not claim that an
unsettled worker was stopped. Pure calls outside a native step retain their
existing lifetime. No Core patch, model change, extra queue, schema migration or
authorization cache is introduced.

## Required qualification

Prove fresh commits visible across ordinary readers and a separate writer,
one audit per content resolution, mid-scope erasure including physical compaction,
nested and inherited-thread retirement, absent-file refusal and Windows handle
release. Then use the current installed Core SDK/registry/adapter pipeline and an
actual immutable Git consumer. Keep real deadlines, source-erasure/revocation
and final-launch checks intact. A faster synthetic result is not whole product,
model quality, daemon or fleet acceptance.

## Native result and next bounded change

The first Git consumer update preserved all 35 logical state/key fingerprints.
The next native attempt timed out during Core's dependency preparation, before
the cycle; a distinct attempt observed Core's normal frozen dependency sync and
bytecode compilation complete, then reproduced launch expiry. Authorization was
recorded at 08:20:59Z, dispatch started at 08:21:23Z, execute-by was 08:21:29Z,
and the first final-launch check failed at 08:21:39Z. No adapter was invoked.
Idle WAL keepers therefore do not by themselves solve the performance failure.

The next candidate reuses stateless source-reader/validator objects owned by each
store, rather than repeatedly constructing their SQLite projection graphs. It
still invokes their current-state authentication methods on every call and does
not retain decoded sources, permissions or validation results. One expression
context method also stops validating the same selection twice back-to-back: its
single authenticated return supplies both the plan and selected source. There
is no intervening await, external callback or operation between those two old
calls. Every later boundary continues its own fresh validation.

Existing erase-during-render, owner withdrawal, superseded selection and final
launch controls must qualify this separately; the prior keeper controls or a
successful warm setup cannot be credited as native readiness for this candidate.

## Bounded qualification

The revised source services passed the expression erasure/withdrawal controls,
source-review recovery, late selection currentness, standard-channel execution,
and the actual current Core source-reading pipeline in an isolated container.
An actual Ubuntu Git consumer then upgraded from the keeper-only candidate to
the revised immutable commit, refreshed its runtime and preserved all 35 logical
state/key fingerprints while delivery stayed inactive. Its installed-source
Core SDK/registry/native test completed in 178.98 seconds including preparation,
performed both 6000- and 15000-character source windows, passed every controlled
model stage and submitted once to the local test adapter. Existing state was
again unchanged; Core and plugin trees were clean and no test process remained.

This is a successful functional reproduction, not a controlled latency benchmark.
It uses controlled HTTP/model responses, no actual inference and no external
delivery. The earlier cold preparation timeout remains recorded separately.
The broad portable pass belongs to the preceding keeper-only runtime; the revised
service lifetime still needs its own broad qualification. Fleet/daemon, active
jobs, real-model usefulness and production acceptance remain open.
