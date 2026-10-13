# ADR 0070 — Let evidenced feedback inform cognition without becoming authority

Status: accepted in isolated kernel; production inactive.

## Gap

Preference-learning estimates existed, but no cognition consumer used them.
Recording a feedback outcome therefore could not inform a subsequent generated
opportunity. The old estimates API also aggregated without a required principal.
It must not become a cross-user prompt input.

## Decision

Require `subject` when reading estimates and apply its filter in SQL before
grouping/decryption. Recheck observation type, immutable row fields, original
content identity/sensitivity, full content digest, target digest and current
source validity. Erased/unavailable observation content contributes no hidden
support mass via another still-readable representative of the same target.

`CognitionLearningReader` advances outcome, reflection and learning projections
in dependency order, then returns at most eight owner-scoped retained advice
entries, each bounded to 1500 serialized characters. Feedback must already have
canonical causal attribution; ordinary replies or delivery receipts cannot create
preference signals. Accepted reflections retain their separate review boundary.
This reader never invents signals from conversation text or performs model calls.
An explicit typed-memory vault does not relocate existing learning/outcome data;
opportunity synthesis keeps that content in its established separate vault.

Opportunity interpretation receives `learned_advisory` separately from explicit
typed `user_context`. Entries expose support/opposition and their original signal
event IDs, not an asserted calibrated probability or permission. The prompt
requires treating them as tentative patterns and not overriding current explicit
preferences. Candidate dimensions carry those evidence IDs; all action authority
still comes from the trusted host and defaults to NONE.

A private HMAC snapshot binds advice to the interpretation start. It is checked
after the model await and on completed-proposal recovery, hence also in existing
selection/expression guards. Retraction, erasure, expiry or other effective advice
change invalidates an old candidate instead of silently continuing its influence.
An old start lacking this field recovers only if current advice is empty; it
cannot retroactively acquire new learned context.

## Evidence and limits

Synthetic causal test constructs two different owners' feedback on the same
target, with opposite directions. Their advice stays separate; public clearance
and unknown owner reveal none. Tampering a projected content ID is ignored.
Erasing one owner's observation removes that advice without affecting the other.
The full interpretation receives only the correct advice and records its causal
IDs; in-flight withdrawal and later recovery are refused. No transport is used.

The interpreter response in this test is a fixture, not proof that a real model
interprets or obeys advice well. The prior action authorization/attempt is likewise
a synthetic ledger fixture, not actual delivery or user benefit. No production
gateway bridge, automatic feedback extraction or ongoing scheduler is enabled.

Reflection accuracy, factual entailment, effect on usefulness, adaptation across
time, complete upstream-content forgetting/derived-copy retention and user-reviewed
learning remain open. Learned presentation styles are not silently activated;
the natural renderer still uses explicit host/user presentation settings. This
change supplies evidenced input to cognition, not authority or an acceptance gate.
