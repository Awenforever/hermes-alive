# ADR0206 — Review-anchored local correction, not whole-message regeneration

Date: 2026-10-23 (Asia/Shanghai).
Status: proposed; private model prototype running, NOT a runtime implementation.

## Actual evidence

A real installed cycle admitted two partial reading findings, generated a coherent
technical explanation and received positive owner feedback on that exact unsent
sample. A subsequent source review legitimately found a narrow attribution error.
Existing correction runs whole-message authoring again: it fixed the attribution
but changed the unrelated opening and formatting into a staged contrast and denser
exposition. The final automatic reviewer approved the factual revision. That is
not proof the revised experience preserved what the owner liked.

Do not disable the valid factual review, ban contrast phrases, enforce shortness
or deterministically replace the one observed phrase. The coupling between local
fact repair and unconstrained re-authoring is the defect. Facts, meaning, utility,
naturalness, owner feedback and sending permission are distinct evidence domains.

## Proposed replacement of existing stages

An opted-in successor of the EXISTING final review should locate exact affected
text spans alongside its factual findings. The host binds those spans to the
reviewed candidate digest, source/context snapshot and review receipt. A span is
an exact unique occurrence, not a model-invented offset; the host computes offsets
and supplies stable IDs. Distinct spans cannot overlap. The model's location and
judgment remain advisory, not proof that every highlighted character is wrong.

The EXISTING corrective author call should return replacements for these span IDs
or abstain. The host constructs the successor from unchanged original segments
and replacements. Text outside the review-selected spans is preserved exactly by
construction; the correcting author cannot restyle the opening or rewrite other
unflagged paragraphs. This is not a guarantee that the review chose minimal or
correct locations; qualify localization separately and preserve its failures.

No safe localization, ambiguous/foreign anchors, missing replacements, overlapping
targets, changed source/candidate/owner context or unsafe protected-literal changes
mean unavailable repair, not a deterministic summary or another provider loop.
Broad unsupported content may need abstention or a fresh intent, not forced local
editing. Actual provider fallback remains Hermes-owned.

Every corrected result still needs the existing full final-wording fidelity/source
checks and fresh send-time authority. A positive opinion about an unsent draft is
neither factual approval nor authority for its successor. Existing user-confirmed
wording must NOT be auto-corrected under the old confirmation; require a new one.
No physical FIFO, transport retry, storage backend or extra production judge is
introduced. Preserve original/revised candidates and their separate receipts.

## Version and recovery requirements

Before inference, explicitly bind the new review schema and correction method to
the operation. Old starts, verdicts and correction contexts keep their recorded
contracts; do not add inferred spans to an old verdict or rerun a failed historical
operation to manufacture success. New results retain exact candidate/source/owner
bindings and expiration/erasure dependencies. Preparation and review approval still
do not authorize sending or prove delivery.

## Prototype and qualification, not a release claim

The private diagnostic reuses the first actual draft and its original public-source
review input, without revealing prior verdict, owner rating or later rewrite to the
successor reviewer. Two logical calls at most: factual review with spans, then
span-only correction. It uses already configured Core models and authorization,
never production writes or messages. Expected locations are not supplied as gold.

Evaluate actual issue detection, exact/nonoverlapping localization, immutable
unaffected text, factual correctness after edits, retention of useful expression
and graceful abstention. Different actual routes are a confound for latency or
style superiority claims. A single success cannot qualify the general mechanism.
Then test foreign/stale/withdrawn/expired/erased inputs, malformed responses,
multiple and repeated spans, Unicode, links and protected literals, crash/reopen
without new inference and actual installed integration before activation.

Current broader objective remains unchanged: useful sustained agenda and learning,
layered/external memory, new representative complete quality rounds, real platform
lifecycle/migration/rollback and final production acceptance remain open.

## 2026-10-23 — Prototype result and superseding corrective-author design

This section supersedes the initial two-stage protocol proposal above; it does
not rewrite historical results. The proposed five-field factual reviewer returned
supported with no correction spans on the known attribution defect. It took one
logical call and never invoked the second author. More review calls did not prove
better detection; preserve this failure rather than relaxing the gold assessment.

A second bounded diagnostic instead reused the original valid negative review and
its exact original candidate/source evidence. Only the existing corrective author
was replaced. One real configured-primary call returned a small exact-span change
that attributed the secondary-source result correctly. Opening, lists, explanation,
scope judgment and source link were copied unchanged. No owner rating or expected
span/replacement was supplied. This is one successful diagnostic, not proof of
general factual judgment, fresh installed integration or a complete quality round.

The development successor therefore leaves the four-field source-review contract
alone. A new corrective-author start freezes `review-anchored-edits-v1`, receives
the retained negative findings plus original grounding and meaning, and returns
exact unique substrings, issue indexes and replacements (or explicit abstention).
Issue indexes refer to unsupported claims followed by uncertainties; each issue
must be localized. The host computes non-overlapping spans and copies all other
characters exactly. It rejects whole-text rewrites, ambiguous/foreign/missing edits,
unchanged negative output and lost protected literals. It cannot prove a proposed
span is semantically minimal or that a replacement is true; the existing full
fidelity and final source/value review must still assess the resulting message.

No extra provider step is added. Scope failure or broad feedback can produce
unavailable correction rather than forced local edits. This is not a transport
fallback. Actual provider routing/fallback stays Core-owned. The new expression
records its actual corrective model, original ancestor and separately reviewed text.

Reconstruction evidence uses the existing encrypted content vault and append-only
journal, with candidate/source/review/context digests, subject/sensitivity, expiry
and actual model provenance. Final-support and recovery resolve the original
negative review and edit evidence afresh and reproduce the exact result. Erased,
withdrawn, expired or stale evidence invalidates descendants; proof bytes are not
delivery authority. Existing historical correction starts without the new method
remain on their original authoring contract; failed/incomplete starts cannot gain
a new inference or retrospective local-edit evidence. New method is not a user
switch for changing the contract of an already started operation.

Status of this successor: implemented in the development tree, focused controlled
qualification in progress. Not installed in production, not released, no actual
sending; full real lifecycle and quality gates in RELEASE_ACCEPTANCE remain open.
