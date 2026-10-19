# ADR 0178: complete the semantic-review contract and recover it once

Date: 2026-10-18. Status: implemented; canonical qualification pending.

## Problem and decision

A real source-to-expression diagnostic reaches semantic review, which labels one
atom both preserved and at risk of omission. Validation correctly rejects that
contradiction. The prompt specified only that an unpreserved atom needs a risk,
while validation also forbids risks on a preserved atom. Fully state that
bidirectional contract, complete atom coverage, unique/known IDs, exact fields
and boolean types. This is a missing interface obligation, not permission to flip
the model's flag, erase its concern or accept a malformed review.

Reuse the existing bounded model protocol-correction pattern in this SAME review
stage. Render once. Review against the unchanged meaning and candidate; if pure
review-shape admission fails, allow one complete corrected assessment against the
original evidence and failed output. Both reviews share the original review-stage
deadline. Do not extend the render deadline or reset the review budget. Current
owner/source/meaning/style/correction-context checks run before and after awaits.

Provider, attribution, independence and host-scope errors are not protocol errors.
A valid negative review is not retried to obtain approval; a corrected negative
review stays negative. Oversized correction input fails rather than truncating
evidence. A second invalid assessment fails. Terminal operations cannot spend
again on reopening. There is no new judge, provider registry, sender or queue.

## Durable evidence

Preserve the original review input, failed review and actual initial route in the
existing encrypted vault, bounded by candidate expiry. Journal only structural
references, hashes, scope and models. Bind the correction event to the actual
candidate and attach its reference to the authenticated final review receipt.

On reopening, verify owner, cause, lifetime, request/prompt digests and authenticated
artifact. Rerun versioned pure admission to prove the original output really was
invalid. An authenticated label is not enough. Reject false failure artifacts,
missing/foreign references, stripped markers with orphan correction events, and
erased evidence. Check retained failure evidence around the corrective await too.
Keep the v1 prompt/admission contract available for historical recovery proof.
Normal historical reviews without correction retain their existing authentication
and semantics; accepted wording and past failed operations are not rewritten.

## Qualification and limits

Focused controlled suites cover malformed/contradictory/unknown/duplicate/typed
fields, successful and negative corrections, valid initial negatives without a
retry, disabled/oversized recovery, provider failure, withdrawal before/during
correction, cancellation, shared timeout, erasure, no-respend replay, privacy,
false failure artifacts and stripped authenticated markers. Adjacent review-store,
expression-runtime, literal-policy and final-wording repair suites pass. Pure
tests qualify mechanics, not semantic intelligence or recipient satisfaction.

A single new actual Qwen call receives the previous failed review's exact original
meaning/message and its invalid assessment under the completed contract. It
returns an admissible NEGATIVE assessment. Preserve that result; contract recovery
does not mean automatic approval. This isolated diagnostic does not resume or
rewrite the failed historical operation and is not a fresh complete chain, replay
qualification, final source review, delivery authorization or acceptance round.

ADR0177's terminal canonical regression is6a08f93/treeb0af5bbc:65 retained logs,
source555/repository578 with exact archive permissions. The original long-term
memory/agenda/feedback, host lifecycle, migration and ten fresh complete clean
round requirements remain open. No production/model/Core/other-plugin change,
deployment, restart or message send is implied.
