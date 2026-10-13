# ADR 0091 — Source presentation belongs before selection and authorization

Status: bounded kernel implementation; no production deployment or full-chain qualification.

## Remaining route identified after ADR 0090

The independent expression LINK atom protects model expression, but original
draft contracts can also cross SendTimeAuthorizer and DispatchOutbox. Those
contracts previously contained only model text. Fixing the expression branch
alone cannot establish source continuity for direct original-draft delivery.

New opportunity synthesis builds a canonical_source_v1 presentation before
creating the candidate, selection frame or user confirmation. When the exact
canonical URL is absent from model text, it appends one in-message source link.
Ordinary destinations use angle-bracket Markdown syntax, preserving parentheses;
destinations containing angle brackets/newlines remain exact plain text rather
than being shortened or replaced. Model text containing the URL remains unchanged.
This is provenance composition, not model-failure fallback or semantic correction.

Original model text stays separately encrypted in the accepted proposal bundle.
The bundle records source_presentation so restart recovery reconstructs exactly
the same content contract. Historical model_text_v1/missing-policy bundles keep
their original contracts. No launch-time mutation, new recipient or permission is
introduced. Selection/source/authority validators compare the reconstructed
contract against the immutable selected frame as before.

Literal presence is not a full Markdown destination audit or proof that a source
is reachable/true. An original draft with the URL as a substring is not rewritten;
malformed/incorrect links and actual platform rendering still require evaluation.
Historical already-authorized no-link contracts are not silently rewritten either;
their upgrade/migration treatment needs a separate audited lifecycle policy. This
implements continuity for newly minted contracts, not a blanket historical guarantee.

## Capacity and representation defects found by broader testing

Adding a valid long source can exceed the generic CycleCandidate JSON limit of
4000 characters even though the channel contract already allows 12000 text
characters. Typed, successfully parsed hermes.channel.send contracts now have a
12256-character serialized-envelope cap. Generic/invalid content retains 4000;
whole-frame 16000 and existing prompt boundaries remain unchanged. This does not
grant side effects, bypass source checks or enlarge total cognitive context.
Escaping-heavy text may still exceed the serialized cap and is rejected, not
truncated. Many large candidates can still exceed the frame limit; no unbounded
collection is accepted.

The original source-aware contract can also exceed SemanticAtom's 1600-character
PROPOSED_CONTENT budget. Expression now retrieves the exact accepted model
proposal by its stable operation/index candidate identity from the verified,
owner-scoped encrypted bundle. Original model wording forms the first atom;
canonical source is a separate LINK atom when absent from that wording. The
selected action/frame remain unchanged. This is not an oversized model utterance
or post-confirmation alteration. Existing source/profile/learning, digest, expiry,
clearance and current-selection checks remain mandatory.

## Verification and evidence

Windows source-presentation tests preserve original encrypted wording, reconstruct
new and historical contracts on reopen, avoid duplicate literal links, exercise
parentheses/long/unrepresentable URLs and unknown policy rejection, and assert
no real attempts, preferences or dispatch. Typed 12000-character text is accepted;
oversized text, oversized generic data, routing-field injection and escaping-heavy
serialized envelopes are rejected. Short and long current contracts pass selection
and expression meaning binding with original wording/source split and immutable
frames. The long-source test originally exposed the 4000-character cap and was
retained as a regression after the typed capacity correction.

Two additional authorization/outbox fixtures prove source-aware direct contract
and explicitly confirmed expression reach the launch-validation boundary with
the exact approved content and unchanged frame. No transport, true authenticated
host grant or delivery acknowledgment is used; these are synthetic fixtures.
Windows synthesis/recovery/cognition and targeted execution tests also pass.

Six retained public synthetic outputs from ADR 0090 are replayed offline through
the new presentation contract. One missing-link output gains provenance, the other
five remain unchanged; all retain one communication candidate and one abstention
with NONE authority. This uses no new inference, selection or dispatch. It does
not assess semantics or retrofit the original experiment's completion/quality.
Fresh vault keys create different keyed identities: the first exact-ID replay
assertion fails. The second explicitly remaps source IDs and preserves text and
judgments; original weighted advice is not reconstructed. These limitations are
recorded, not presented as original-journal recovery or migration proof.

Replay report SHA256:
48e4ff9b9c3ebf8161c2fd4f2fd1a8776fc329e8f412c4b603835ab2c4f97be3.
Initial snapshot tree ef7a85ee57235c9dccb996f652aef59878b3b1f4; archive SHA256
a3c38e40d7baa81bdc6218c8696ed6f704279741441ad4a9d6e9fe0ba3f357ba.
Nine isolated Linux suites pass, container
alive-source-presentation-offline-20261014-r1 exited 0,
2026-10-13T19:05:26.032253348Z to 2026-10-13T19:06:22.746829133Z.

Final code snapshot tree eaa406efb66fea3a5357c0680348d84498157f87; archive SHA256
1dd44dace60e5780ddd3af553ef79cf6afa01c66d1212fd53745d4bcd259454e.
Final isolated suite outcomes are appended after actual terminal verification.
These tests do not qualify install/upgrade/rollback or production functionality.

Final snapshot passes twelve isolated Linux suites: opportunity_source_presentation,
cognition_cycle, semantic_rendering, semantic_review, opportunity_synthesis,
opportunity_recovery, opportunity_abstention, opportunity_expression,
opportunity_execution, advice_pairs, learning_context and live_learning_contract.
Container alive-source-presentation-offline-20261014-r2 exited 0,
2026-10-13T19:15:30.573875133Z to 2026-10-13T19:16:30.610318852Z,
with network disabled and scratch read-only. This covers final source/wording
separation, typed capacities and execution-boundary fixtures, not real delivery.

Actual model totals stay 83 logical / 95 observed async HTTP attempts. No new
model profile exported, provider called, private chat read, production deployment,
wmw/other-plugin/model/channel/configuration change or real send. Production
running/start rechecked unchanged at 2026-10-11T07:43:25.630569081Z.

## Next critical path, unchanged objective

Qualify source/decision semantics and natural rendering on useful new contexts,
including redundant questions, conditional usefulness and unsupported pragmatic
claims. Then integrate useful attributed outcomes and bounded feedback learning,
not silence/delivery as enthusiasm. Genuine host ingress/grants/delivery, full
layered/external memory, sustained agenda/adaptation, physical forgetting,
migration/rollback, portable lifecycle and production acceptance remain required.
