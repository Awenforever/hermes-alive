# ADR-0064: Completed candidate recovery is not reauthorization

Status: accepted for retained shadow candidates

## Problem

Interpretation retained encrypted accepted drafts but exposed no recovery API.
Re-running inference is fenced by the durable start receipt, correctly preventing
repeat spending; callers nevertheless need to recover an unambiguously completed
result. Partial rejection also compressed proposal positions, so reconstructing
candidate IDs from the saved list alone would change their original identities.

## Decision

`load_completed` reads only a matching owner/clearance, actor/source and causal
start/completion pair with no failure receipt. Current authenticated discovery and
explicit user context must match the original evidence identities. It verifies
the retained bundle's scope, deadline, digest and bounded proposal/count schema.
It invokes no model, appends no journal event, selects nothing and cannot send.

New bundles retain accepted proposals' original positions, keeping candidate and
content IDs stable across partial rejection, restart and repeated load. Existing
accepted-only bundles with zero rejections remain unambiguous. Legacy partially
rejected bundles lack recoverable original positions; refuse rather than invent
new identity, overwrite history or regenerate without an explicit new operation.
Their historical data is not deleted by this refusal.

Recovery defaults to NONE authority. Fresh host input may reassert the original
authority, never upgrade it. Stored delegation is not revived automatically.
Erased, expired, withdrawn, superseded, incomplete or ambiguously completed work
is refused. A safe return is still only a draft/intent input, not authorization.

## Evidence and boundaries

Regression tests preserve identity after a rejected first proposal, true model
attribution, original rejection counts and no repeat inference/journal append.
They reject foreign/low-clearance requests, authority upgrades, missing completion,
erased bundles and context withdrawal after completion. Private text stays out of
journal files. The separate opt-in synthetic live probe composes recovery and a
single model-selection call, never dispatch or channel activity.

Recovery is not atomic with later networking or authority changes. Source/profile
freshness still needs end-to-end binding through selection, presentation and
send-time policy. Arbitrary host journal tampering, generalized key rotation and
legacy partial-bundle identity reconstruction are not solved. An inspected old
selection is not automatically current intent or proof of benefit. Production
scheduling, installation qualification, natural presentation, outcome learning and
longitudinal human usefulness remain separate gates.
