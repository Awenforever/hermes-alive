# ADR 0263 — Correct the argument that failed, not an imagined prerequisite

Status: bounded installed-Core argument/lookup qualification passed; real intake
corrected, full continued-work qualification still pending.
Date: 2026-10-28.

## Real-model counterexample

r258 retained the synthetic two-phase owner request, selected the inherited Core
main/fallback models and allowed no messages or production writes. The first
main record call abbreviated its evidence_span. The exact-span validator
correctly refused it, but the generic error incorrectly suggested an explicit
future time. The model fixed its span and also invented available_at. The item
was saved with that unrequested future deferral, so all five Native wakes made
zero logical model calls and submitted zero jobs. The test failed its work gate.
This was an intake/recovery failure, not evidence about later-step competence.

The later main query also passed a provenance request-event ID to the share
reference reader. The original existed, but that reader does not read task
requests. The answer wrongly suggested the original could not be retrieved.
Do not relax source ownership or turn an arbitrary journal ID into a reader.

## Correctable argument errors are distinct from unavailable authority

Preserve Core-turn correlation, owner/delegation checks and literal evidence.
Split a mismatched/abbreviated evidence_span from a missing current Core turn.
Return a typed field error before admitting mutation; tell the caller to copy a
contiguous exact current-owner fragment and correct that field. Do not suggest
inventing a time or changing permission to fix a literal-span error.

Input time errors identify the supplied field and actual validity/order/retention
constraint. Omitted times remain valid. available_at represents an owner-requested
deferral, not ordinary permission to work on a future wake. Generic unavailability
does not establish that a time is missing. This corrects the machine interface,
not user prose with a keyword filter, inferred date or canned reply.

## Typed lookup capability at the source

An agenda item returns original_request_lookup with the real tool name and exact
list arguments. Its existing original_source_available flag still determines
whether the body is retained; a lookup does not restore erased data. Provenance
event IDs are not share-reader handles. The share-reader schema explains that
boundary; its uniform privacy-preserving unavailable result is unchanged.

## Qualification scope

The installed Core dispatcher must refuse a bad literal span, invalid/naive time,
reversed times and a time outside retention without source/item/job mutation.
Corrected literal intake without dates must be immediately eligible, and its
returned lookup must retrieve the exact retained original in the admitted owner
conversation. Re-run the same real-model questions and work scenario against the
new runtime; preserve r258 as failed. Do not change the owner request, move the
clock forward, erase the invented deferral in that failed profile or manually
create work to turn the old test green. All private reports require the normal
terminal container and credential-audit gate before inspection.

r259 passed five controlled actual-Core cases and cold checks. Its argument
feedback case rejects the listed invalid inputs before journal/item/job mutation,
then records the corrected exact request without dates and retrieves it through
the returned typed capability. The original process and container finished with
exit 0; destroy/absence and clean Core supplier were independently checked.

The unchanged-request real-model r260 rerun saved no available_at or deadline,
retained the original project A while main was in project B, and returned the
typed original-request lookup. It nevertheless failed continued work: later
decisions treated the historical registration turn as current and created zero
jobs. Preserve this as a failed full workflow, not a passing chain inferred from
corrected intake. ADR0264 addresses that separate temporal-input boundary.
