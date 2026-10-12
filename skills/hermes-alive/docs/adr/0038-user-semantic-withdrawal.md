# ADR-0038: User inspection and durable semantic withdrawal

Status: accepted for shadow kernel; production activation pending

## Decision

Expose meaning inspection and withdrawal through the existing Hermes-native
`/memory alive` control surface. The host supplies the authenticated user;
message text and model output cannot nominate another user's identity.
Check ownership before decrypting meaning content.

`/memory alive message <meaning-event-id>` shows typed atoms and source event
identifiers. These references establish provenance, not factual entailment.
`/memory alive withdraw-message <meaning-event-id>` writes an installation-key
authenticated, permanent withdrawal event. Withdrawal is idempotent and can
only be requested by the owner. It is not a content-erasure operation.

All subsequent meaning resolution rechecks withdrawal. Deterministic renders,
model candidates and semantic-review receipts therefore lose validity even
if previously accepted. Restart cannot recover withdrawn meaning for use.
Malformed withdrawal evidence fails closed rather than silently resurrecting
the content. Keep the historical event chain for explanation and use the
separate forget operation for encrypted-content erasure.

Withdrawal stops future use after revalidation; it cannot delete an already
delivered platform message or recall a request already handed to a remote
service. No such capability is claimed. This kernel remains disconnected
from live delivery; a future bridge must revalidate immediately before its
dispatch boundary and document in-flight limits.

## Evidence and scope

Focused tests cover owner inspection, cross-user refusal, repeated withdrawal,
reopening the store, deterministic-render invalidation, and invalidation of
an otherwise valid independent-review receipt and encrypted model candidate.
Anonymous access and forged withdrawal evidence are refused; withdrawal keeps
the encrypted historical document, establishing that it is not erasure.
The journal retains structural withdrawal evidence without raw atom text.

On 2026-10-12 the user-controls, semantic-rendering, semantic-review-store and
retention tests passed locally on Windows and in a disposable container based
on production image `hermes-agent:v0.21.3-weekly-20260918`. The container had no
network, mounted only test source read-only, and did not mount production data.
Production stayed running with the same start timestamp throughout; it was
not deployed or restarted for this milestone.

This is the inspect/withdraw baseline, not the entire sovereignty objective.
Correction/replacement, discoverable message identifiers, user-visible live
delivery controls and production end-to-end acceptance remain unfinished.
