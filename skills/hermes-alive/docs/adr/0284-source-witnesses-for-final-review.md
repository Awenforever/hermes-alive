# ADR 0284 — Bind final factual judgments to retained excerpts

> **2026-11-05 注（Codex，非原文）**: Audience: maintainers and QA. Purpose: architecture decisions, historical evidence and qualification limits.

Date 2026-11-04. Development candidate.

An isolated real-model trial passed the final review even though the share
implicitly joined a benchmark and a demonstration from different setups.
The exact text and excerpts were still available in two Core follow-up
turns. The mismatch arose in the assessment of the relationship between
claims and evidence, rather than loss of conversation history.

For new discovery reviews, require the assessor to identify exact spans
of the outward wording, then cite contiguous passages from retained
evidence using source event IDs. Supported facts require witnesses even
when the communication judgment is negative. The host rejects missing,
invented or misbound spans. This does not mechanically prove entailment.
The assessor checks relationships between clauses, such as whether the
same setup supports a measurement and a demonstration. Missing material
qualifications can remain uncertain.

The new scope preserves earlier prompt and replay contracts. Witnesses
stay in the existing protected review receipt and are rechecked before
execution. Use the existing format recovery and stage budget. A quote
proves access to a passage, not independent confirmation or authority.

Verify with a controlled forged-witness regression and real trials where
correct details can be combined into a misleading claim. Sharing quality
still requires inspecting the original output and its evidence.

In the first real trial, seven witnesses matched and one source quote
did not. The strict check withheld submission and the format recovery
ran out of its stage budget. The next immutable contract presents
numbered contiguous passages and asks the assessor to select a number.
The host inserts the exact original text and verifies it on replay.
This removes source transcription from the response contract. Claim
spans still match the proposed wording, and the assessor still judges
whether the evidence supports the claim in its full context.

The next real trial returned all six claim spans verbatim, but selected
passage 15 from a source with only 13 passages. The host withheld
submission and the bounded correction expired. A new scope labels
each visible passage with a unique ID within the review snapshot.
The assessor selects that single ID. The host resolves and retains both
the original source event ID and exact passage, then verifies the
association on replay. Historical index-based receipts keep their
original validation. The new scope still requires live qualification.

A real regression used valid labels after one response-format correction,
then submitted to a local adapter. Two installed Core turns recovered the
topic, but the first described a plausible implementation as if the team
had reported it. The second distinguished claims from results and corrected
the first. The continuity prompt now asks the main model to mark analogies
and disclose missing evidence before interpreting it. This preserves the
existing Core conversation path. Source-label validity and later correction
alone cannot qualify the first follow-up.

Later trials repeatedly placed recipient evidence inside both assessment
dimensions. A new version uses one flat response schema, with a single
recipient-evidence field and distinct judgments and reasons. The host maps
it to the existing validated receipt, preserving older contracts. The
factual judgment explicitly checks comparison baselines, experimental
conditions and whether an adjacent example actually used the cited test.
The first follow-up should answer the user's question at its requested
depth. Live checks still have to establish both factual and conversational fit.

The native accessibility-tool trial supplied the approved timeframe and
region in the final review snapshot. The reviewer justified recipient fit
with technical clarity and an interesting benchmark. It did not establish
that the selected project matched the timeframe and region or explain
a concrete reason to pivot. The original result therefore stays outside
the qualifying streak. A future version should record search-purpose
alignment separately from recipient fit. It should allow a justified
background pivot and distinguish it from a direct match. General interest
or the availability of a related article cannot substitute for that judgment.

The new immutable review contract records a third model judgment in the same
existing assessment call. Search alignment distinguishes a supported match,
a justified pivot, a conflict, unresolved scope, and an absent search purpose.
The reviewer must ground a pivot in an actual conversational need and the
source's accurately represented role. No keyword, region-domain or date regex
decides relevance. Recipient preferences remain soft evidence, not a filter.
The host preserves the separate reasons, refuses conflicts, and retains
uncertainty rather than upgrading it to a match. Supplied queries cannot be
dismissed as not applicable. Existing source witnesses and authority checks
remain mandatory, and earlier receipts keep their original review contracts.

Controlled regressions establish combination, replay consistency and missing
judgment rejection. They do not establish model judgment quality. Fresh real
source trials and follow-up evaluation remain required before any quality credit.

The actual Core controlled source-reading chain also exercised independent
search conflict and uncertainty while keeping factual support and communication
fit positive. Each retained the negative final review, reached content-review
attention after an explicit correction abstention, and created no authorization,
dispatch start or adapter call. The matched-source correction path still passed.
These tests establish propagation through the runtime, not the accuracy of the
model's relevance judgment. An actual November accessibility search produced no
candidate from its three results and stopped before final review; it earns no
quality round and does not qualify that new assessment contract.

## Fresh solar-observation trial

Real Core r893 used a new public solar-observation query and inherited model
routes. After two limited first reads, the bounded refinement returned two
reports on the AIMS result. The final review accepted factual support, recipient
fit and search alignment, and one unmodified draft reached the isolated local
adapter. The private owner data stayed outside the public query-planning input.

The source witnesses supported how the institutional report described the
result. They did not surface the paper's distinction between apparent weakening,
a change in the sampled height, and actual magnetic-field redistribution. The
draft presented the weakening without that distinction. The authors explicitly
leave the relative contributions unresolved in their
[paper](https://arxiv.org/abs/2610.33502). Treat this as a failed factual
qualification. A matching report excerpt establishes what was reported.
Method, measurement and interpretation require the relevant original evidence
or wording that retains the uncertainty of the narrower evidence.

The retained inputs held report extracts and no paper extract. The refinement
query was topical and sought another institutional source. Before spending a
second review on the same report evidence, qualify the bounded refinement and
read-selection stages on locating a named underlying study or technical record.
Exercise cases where the underlying record is accessible, inaccessible, or
disagrees with the report. The third case must show that final wording carries
the relevant limitation. Keep the existing public-only scope and read limits.

The follow-up harness stopped before inference because its tool allow-list
predated the authenticated feedback tool. Correct the fixture to account for
the current tool contract while proving that unconsented feedback cannot be
recorded. This round earns zero fresh quality credit.

## Carry the evidence question into the final bounded read

The optional refinement now asks what a technical claim rests on and whether
the direct record could answer a material question. When it uses its one public
query, the final reader receives that exact query and the public-only planning
reason. It also sees the collector's scope for each input, so a listing is
distinguishable from an extract. The reason guides selection and carries no
authority or factual weight. The existing source references, read budget,
consent and public-input checks still apply. Previously started choices retain
their original input and prompt on replay.

The controlled conflict fixture supplies a report that claims an effect was
measured and a study that says only a proxy was measured. It checks that both
extracts reach the retained reading group when the selector chooses the study,
including after cold replay. The inaccessible-original fixture checks that a
failed read does not become retained evidence. These checks establish the
selection handoff and evidence retention. A real model must still show that it
chooses the direct record and preserves the qualification in the final wording.

The exact prior discovery implementation (3587aa7) wrote the older prompt
snapshots and retained conflicting sources. A new discovery cycle using cba8a65
reopened that journal and recovered the same reading receipts without model
inference or web calls. Separately, the exact installed cba8a65 candidate on
pinned Hermes Core ran the controlled source-depth journey through the final
review and isolated adapter. It recovered a qualification beyond the old
read window. That journey used synthetic sources and model responses.

## Real replay reached the publication, with incomplete evidence

The r914 replay selected the cited DOI directly under the same public budget.
Core extracted 15,177 characters from the publisher page. They began with
the data availability statement and included references, figures and citation
metadata. The text omitted the paper's account of line-formation height and
field redistribution. The current evidence therefore supports a visit to the
paper and some details from it, but cannot supply its material interpretation.
The [author manuscript](https://arxiv.org/abs/2610.33502) gives that distinction
in its abstract.

The draft opened with a direct field-weakening claim and added the word
“apparent” later. The final assessment accepted both parts using the press
release and the paper title. That is a factual acceptance failure. Qualifying
the claim later did not correct the force of the opening, and a title was not
evidence of the missing explanation. Two ordinary Core follow-ups ran. The
first used the qualified result but stayed dense for a one-sentence request.
The second distinguished instrument claims, observational data and simulation,
and acknowledged the missing methods. Its claim about the comparison baseline
still needs a direct witness. Feedback remained disabled with zero records.
There was no physical delivery and this repeated query earned no fresh credit.

The next changes should address two independent seams. Source acquisition
must distinguish substantive passages from ancillary material and use an
accessible copy when the already granted public reading budget permits it.
Final assessment must evaluate the strongest claim the reader encounters,
including its opening and any later qualification, using only the material
actually retained. A weaker, attributed claim or abstention remains valid
when the decisive evidence is unavailable. A new reading allowance would
require its own explicit policy choice. Cover conflicting primary and
secondary text, an incomplete publisher extract, a useful open alternative,
and the absence of any usable alternative.

## Claim scope in the final assessment

New discovery receipts bind the v10 review contract. The same final review
call explicitly judges whether the strongest material assertion stays within
the retained evidence. A conflicting headline or opening is evaluated where
it appears. An incompatible caveat elsewhere does not repair it. The assessor
distinguishes direct measurement, proxies, explanations and attributed reports.
An overstated assertion yields an unsupported verdict, and an unresolved
material scope yields an uncertain verdict, even if the other judgments pass.
The host reconstructs that result from retained findings when reopening it.
Historical contracts preserve their previous prompt, wire shape and verdict.

This is a decision within one model review. Passage identity is validated by
the host, while the meaning of the passage and the scope judgment still
depend on model quality. Substantive extraction and real-model qualification
are open.

## Accessible copies within the public reading budget

With public refinement and deeper reading already enabled, the planner can
use its optional query to look for an accessible author copy or direct
technical record. It can reserve one already cited URL for the same
follow-up. The host then excludes that URL from the search-result choices and
reads at most one additional result. An empty search can still leave the
reserved citation available. The total allowance stays at one optional query
and two optional reads. An unresolved worker cannot start another read.
Selection uses retained public citations and search results, with the normal
Core URL checks. Historical decisions keep their original mutually exclusive
actions and cannot acquire a reserved citation on replay.

The collector still returns excerpts. An accessible URL and a successful
response do not establish that a useful passage was retrieved. The final
scope assessment remains responsible for withholding assertions that the
available evidence cannot support.

The independent r919 VLM trial used the earlier runtime. A real public query
and final read selection sought an official model page. The candidate focused
on an adjacent computer-use demonstration. Final review found that it did not
establish the original search's released open weights and visual-grounding
capability. No adapter submission or follow-up took place. This proves real
use of the query-to-selection handoff and a review rejection, with no fresh
quality credit. A useful unexpected discovery remains eligible under the
existing justified-pivot contract, which needs further real calibration.

In r921 the first search returned a topical listing and a general home page.
The planner issued a follow-up query using the headline's wording and the
institution, without reserving a citation. It read two institutional reports
and neither contained the authors' distinction. The final scope judgment
accepted a direct weakening claim attributed to one report. That passes
literal attribution but fails material scope: the opening and the asserted
implication of the measurement were stronger than the underlying result.
Both ordinary follow-ups ran. The second explicitly admitted the absent paper,
but its wording also turned the reports' silence about cross-instrument
comparison into a negative claim about the study. This regression failed.

The combined read option is qualified as a bounded capability. Real model
selection and review are still open. A follow-up query derived from a report
headline can retrieve more descriptions of the same strength; prioritization
should carry a specific missing distinction or primary identifier into source
selection. The factual evidence check must evaluate how the draft presents
the reported finding and what it makes of it, including attributed prose.
Further calibration needs both genuine overclaiming and legitimate concise
attribution, along with independent fresh cases. A repeated solar case does
not increase the sharing streak.
