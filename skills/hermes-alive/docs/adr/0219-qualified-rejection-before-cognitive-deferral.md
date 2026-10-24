# ADR0219 — Qualified rejection before cognitive deferral

Date: 2026-10-24 (Asia/Shanghai), Codex.
Status: proof classification implemented; source eligibility/recovery still open.

The existing `content_review_attention` outcome conflates a completed negative
assessment with cases such as unavailable repair. Repair can fail while physical
provider work remains unresolved. Continuing on the disposition alone would turn
unknown work into an implicit retry; calling all such cases silence is false.

`SendPreparationRuntime.rejection_witness` now reads current retained evidence
without inference. Only exact final semantic rejection, unsupported wording or
material uncertainty can produce `QualifiedContentRejection`. It binds owner,
operation, selection, exact expression, completed review, source identities and
their bounded validity. Changed wording/selection, missing or erased ancestry,
foreign scope, unavailable repair and pending model work do not qualify.
User-admitted commitments are not optional public discovery and do not enter
this proof path. A negative review remains advisory, not a claim that a source
or topic is bad and not authority to ignore the owner or send something else.

The source-review protocol retains historical events without an envelope expiry;
the encrypted review content inherits the actual rendered expression's lifetime.
Check that exact retention contract rather than assuming every event has a TTL.
Semantic-review expiry, expression validity and source validity remain enforced.

Both shadow and executable cycle composition attach this optional proof only to
content attention, through the host's context-read capability. The existing
authenticated host completion retains the reference-only payload, checking owner
and operation. There is no new queue, scheduler, metadata-only permission or
duplicate store. Missing metadata in old completions is not negative evidence.
Every future eligibility use must revalidate the underlying retained proofs;
the payload is not a permanent suppression certificate or a replacement review.

This does NOT yet change the continuous host's stop behavior, snooze a source,
filter the opportunity pool or claim full recovery. Next consume the qualified
history for bounded attempt eligibility: preserve original facts and failed
wording, permit other useful opportunities, reconsider after relevant context or
material changes, and handle exhaustion without repeated regeneration. Do not
globally park merely because one selected draft failed. Existing active evidence
also serves retained grounding, so hiding it globally is not an eligibility API.
Prefer the existing agenda/journal over a parallel lifecycle or physical FIFO.
