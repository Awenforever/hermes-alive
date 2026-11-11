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
