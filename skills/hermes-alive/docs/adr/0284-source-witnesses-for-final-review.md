# ADR 0284 — Bind final factual judgments to retained excerpts

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
