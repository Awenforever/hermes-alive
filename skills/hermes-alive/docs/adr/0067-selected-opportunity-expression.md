# ADR-0067: Express the selected draft without manufacturing a new intent

Status: accepted for owner-scoped shadow expression

## Problem

Generated opportunity selection retained a channel-action draft, while semantic
review accepted only frames originally containing semantic-message references.
Replacing a selected frame, making a second choice, or claiming a model-extracted
meaning was proven fact would lose the original intent/provenance boundary.

## Decision

`OpportunityExpressionStore` specializes shadow review for generated SHARE/ASK.
It keeps the existing frame, action contract, authority and selection immutable.
The authenticated meaning identity derives from that selection. Its single
`proposed_content` atom retains the complete selected draft, its original evidence
and selected event; it is not promoted to a fact. The 1600-character draft boundary
matches interpretation; other atom kinds retain their existing 1200 bound.

The current source URL, when present in the draft, is an exact protected literal.
Other claims, relations, quantities, uncertainty and negation remain in the whole
draft for semantic comparison, not keyword extraction. This avoids adding a
second generative extraction stage that could silently alter meaning. The single
atom is not a claim of fully typed semantic decomposition or factual entailment.
Large source URLs within the bounded proposed draft remain protectable.

At creation/recovery and every comparator/model-candidate/review validation,
verify current selected intent, original generated provenance, owner, authority,
retained draft, current discovery/profile sources and retention. Check owner
before decrypting bound meaning. Speech act, full atom/evidence/literal content,
sensitivity and identity must match. Expiry cannot exceed the original bundle.
Repeat definition returns the same verified meaning without another event.

Expression never changes selection or grants action/delivery. Reviews remain
shadow evidence, not permission or proof of truth. No production activation.

## Evidence and remaining work

The composition test uses real journal/projections: synthetic discovery and user
preference, model interpretation, model selection, bound meaning, natural render
and independent synthetic review. SHARE and ASK are positive controls; withdrawal,
source erasure, superseding selection, foreign owner and post-review withdrawal
invalidate retained work. The original frame remains byte-identical; no action.

The opt-in one-call live probe can express an existing actual selected synthetic
draft, preserving prior paid inference rather than selecting again. It records a
durable spend fence and keeps selection/review/delivery accounting explicit.
Its renderer still needs independent calibrated semantic and naturalness review.

Still open: typed decomposition where useful, factual/source entailment review,
full independent reviewer availability/calibration, reviewed-render admission to
policy/dispatch, erasure of all derived copies, outcomes/learning, installation,
production canary and longitudinal human usefulness. Checks are not atomic with
networking or retries inside the Hermes provider. The original selected draft may
itself be wrong; faithful expression does not make it true.
