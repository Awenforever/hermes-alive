# ADR 0276 — Let the existing followup deepen its current source

Date: 2026-10-29. Status: development candidate; not production-qualified.

## Problem

A real public-discovery trial selected a plausible abstract-level explanation,
then ordinary continuation expanded it beyond the evidence. The short Core page
extract omitted a methods section containing a material qualification. A bounded
comparison of Core's actual extraction windows confirmed that the qualification
was available in a larger window. The issue is not specific to that article:
the current optional public followup can search again or follow another citation,
but cannot decide to read its current page more deeply.

Increasing every initial read or requiring complete papers would impose a blanket
cost without establishing semantic correctness. Reading a tool's cache-path
footer as permission to open a file would also cross the host boundary.

## Decision

New public-refinement cycles offer one additional alternative in the existing
followup decision: deepen one already supplied public page. It replaces that
step's search/citation action, not supplements it. The model selects a source
reference and reason; the host resolves the resource and uses the existing Core
`web_extract` capability. It cannot request a local path, invent a destination,
open private memory or gain another followup allowance.

The initial read remains bounded at 6,000 requested characters. Focused followup
resources receive 15,000, whether the model deepens its current page, follows
the existing at-most-two citations, or reads at most two results of its one public
refinement query. Thus finding the primary source in that last step does not
trap it in another short introductory window. There is still only one followup
allowance, with a 16,384-character per-resource retained boundary for Core framing.
This is a bounded larger window, not a full-resource guarantee. Oversized results
are refused, never silently clipped or rewritten. These limits follow the actual
Core default-size diagnostic and the existing atomic research context budget;
they are not thresholds for factual validity or topic eligibility.

The request retains its depth policy before IO. The resulting source uses a
separate window identity, so it complements rather than withdraws the initial
read. Expanded content remains in the existing encrypted observation store.
The original short and expanded readings enter one provenance-bound research
group. The interpreter, factual review and conversation reference use the recorded
excerpt policy consistently; later recovery cannot invent a deeper original read.
Withdrawing or erasing either pinned source invalidates the group.

New cycles pin a depth-selection mode. A cycle whose original search already
started without that mode retains the old prompt, normalized decision and IO
scope. The older excerpt policy keeps its 8,192-character window. Expanded
observations can pass their complete bounded text under the new policy; ordinary
observations keep their original bounds.

## Limits and evidence needed

The model may still choose the wrong read, misunderstand an available passage or
make an unsupported inference. A source's date and novelty still require actual
evidence; search ordering is not recency. No new judge, scheduler, retry queue,
provider or publisher-specific parser is introduced.

Verify alternative-action exclusivity, source and owner binding, larger content
past the old window, no silent clipping, retained legacy scope, atomic group
recovery, revocation, erasure and no repeated IO/inference. Exercise actual Core
dispatch and then inherited-model discovery/continuation. Only useful faithful
behavior can count toward quality acceptance; exposing a new action is not itself
a passed round or whole-assistant acceptance.
