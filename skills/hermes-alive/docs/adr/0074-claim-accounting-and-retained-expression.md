# ADR 0074 — Inspect claim roles and preserve the retained source set in expression

Status: bounded shadow accounting and expression-window repair; no delivery qualification.

## Inspectable assessment, not a stronger blanket verdict

The optional `ClaimSupportReviewer` reuses the source review's owner scope, pinned
input snapshots, retention, actual reviewer independence, method digest and atomic
one-attempt lifecycle. It partitions the retained message into exact ordered text
units, with model-assessed roles (verifiable claim, tentative inference,
recommendation, conversational), support and exact field/index/source quotations.
Stored findings are revalidated against the current snapshot on resolution.

The host verifies quotation presence and ordered non-whitespace text coverage. It
rejects missing/reordered/paraphrased text, nonexistent references, metadata presented
as evidence and learned advice promoted to an explicit user fact. It derives an
aggregate verdict from reported unit support; this does not prove that a quote
entails the claim or that the model extracted/classified all material assertions.
`semantic_coverage_proven` stays false, as does automatic-delivery authority.
An offline deliberately misclassified all-conversational message demonstrates this
limitation, rather than pretending structural validation catches semantic errors.

Whole-message review remains the default. Claim accounting is opt-in shadow only;
it neither rewrites the candidate nor upgrades its host permission. Public model
choice stays Hermes-owned and requires no hardcoded provider or new key.

## Actual retained-candidate diagnostic

One actual independent `claude-haiku-4-5` / `custom:ustc` call returned five units:
two verifiable claims, one tentative inference, two recommendations. Quoted inputs
and full lexical coverage passed current verification; the result was `supported`.
No source truth, correct semantic classification, beneficial action or qualification
was inferred from that result. The original paid candidate was not regenerated.

The final compound unit combines a conditional recommendation with the "no signup
or cost" rationale and the disputed zero-loss wording. The model classified it as
recommendation/not_applicable, explaining that its primary function was advisory.
This reveals an inspection problem: primary discourse function can subsume embedded
assertions. Full text coverage is not the same as material-claim coverage. It does
not independently settle whether the zero-loss wording is pragmatically acceptable.
Do not change an author's label or add a phrase blacklist to obtain a clean score.

Next distinguish a unit's communicative function from embedded factual assertions
and audit those separately on held-out mixed messages. Avoid forcing facts,
opinions, uncertainty and suggestions into a single mutually exclusive judgment.
Account for overlapping/compound meaning without demanding literal sentence copying
as a proxy for truth. No new delivery gate may rely on this unqualified assessor.

## Real expression-chain defect reproduced and repaired

Although generation/selection already validated pinned inputs, expression resolved
the source URL using a freshly ranked top-eight discovery window. Twelve new
higher-priority unrelated observations displaced the valid original source; defining
its meaning then failed with `original opportunity evidence is unavailable`.
The regression explicitly proves the original source is absent from the fresh
window; merely adding equal-priority noise did not exercise this condition.

Expression now resolves the original interpretation's bound observation IDs, with
unchanged current-source checks. It does not pin a source after supersession,
expiry, erasure or explicit-profile withdrawal. Nor does it prevent the deliberator
from explicitly selecting a new intent; it prevents unrelated ranking changes from
silently erasing the currently selected valid intent.

Tests cover window displacement before expression, during renderer wait and during
semantic reviewer wait, alongside existing withdrawn/erased/superseded cases. The
selected frame remains unchanged; no send attempt occurs. This is a repair to a
useful shadow chain, not a production gateway or actual-user-benefit acceptance.
