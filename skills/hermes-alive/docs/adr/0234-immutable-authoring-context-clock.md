# ADR0234 — Immutable authoring context clock

2026-10-25, Codex. Status: candidate; focused and actual-model qualification
pending. This is context grounding, not a new source, execution permit or style.

## Evidence

The actual r84 writer request contains meaning, presentation, language and source
context, but no explicit host current time. Its collected sources had unresolved
published_at values. Controlled writing experiments still described a dated
forecast inconsistently. Asking for more conversational language did not repair
that information gap. The collector clock and publication date are different;
neither proves that a predicted event later happened.

## Decision

New discovery rendering starts record authoring_clock=host-render-start-v1 in
their existing durable start. The authoring_as_of input is that start event's
UTC timestamp. Its prompt explains historical forecasts and unknown updates.
The clock never slides forward when a recorded operation is reopened. A legacy
start without the marker keeps its old input and authoring prompt; unknown
contracts, changed owner/selection or a future host clock fail before inference.

Keep original source text, dates, required meaning, protected literals, owner
scope and review/authorization rules. This timestamp is not a publication date,
proof of recency or factual followup, permission for new I/O, or a renewed permit.
Ordinary non-discovery rendering retains its existing input. No main-dialogue
prompt, model routing, preference learning or transport behavior changes.

## Required proof

Check the actual durable timestamp delivered to the model, stable reopening,
legacy unclocked starts, unknown contracts and foreign scope. Preserve existing
source-withdrawal, protected meaning, correction and protocol recovery checks.
Then use actual configured models on a dated public source and inspect the full
original wording. Correct input alone is not a proven semantic fix or a quality
round; a missing later result must never become a claim that it did not occur.
