# ADR 0077 — Exact confirmed expression reaches the executable contract

Status: explicit-confirmation shadow path implemented; automatic admission and
real external delivery remain unqualified.

## Gap and decision

The expression store retained model wording and fidelity assessments, but every
authorized attempt still resolved the original selected candidate contract. Thus
natural expression was disconnected from execution. Changing the immutable frame
would lose the original intent and make provenance checks unreliable.

Keep the original selection unchanged. A caller may now supply an expression
event to SendTimeAuthorizer. This path is deliberately limited to a candidate
whose original host authority is USER_CONFIRMED, with a later inbound confirmation
from the same owner explicitly binding both selection and expression event IDs.
An approval of the original draft does not approve different model wording. Model
review alone cannot activate this path, upgrade authority or grant automatic sends.

OpportunityExpressionStore checks owner and sensitivity before resolving the
expression, then revalidates the current original opportunity/meaning and exact
text provenance. The destination-free channel contract contains that exact text.
The encrypted derivative has a deterministic identity and cannot outlive the
expression. Its content ID and expression event ID are covered by the authenticated
authorization payload; the contract itself is independently bound by the existing
contract authenticator. No private text or destination is added to the journal.

OutcomeProjection and DispatchOutbox use the authorized executable content ID,
falling back to the original selected content only when no expression was supplied.
At start and pre-launch, the outbox re-resolves the original expression and checks
its exact contract binding. Erasing that expression cannot be bypassed by keeping
the derivative copy. No network writer transaction performs projecting reads.

## Authorization recovery

The operation replay fence also binds expression identity. The same operation
cannot silently switch between original draft and expression. Recovered permits
recheck original input validity and expression binding, not just permit time and
route. A withdrawal returns a denied view of the retained receipt; it does not
rewrite historical permission or delete the original authorization event.

## Isolated evidence and limitations

The opportunity execution suite includes exact changed wording passing through
real authorization, attempt projection, outbox reconciliation, start and pre-launch
APIs; original frame content remains unchanged. It also rejects an unconfirmed
expression, an erased original expression despite its executable copy, operation
reuse without the expression, and cached authorization after profile withdrawal.
All user/model/host records are synthetic and the route is test-only. No model or
transport is called and no delivery success is manufactured.

This is a useful explicit-confirmation path, not the final autonomous architecture.
Its user confirmation does not establish source truth or user benefit. Remaining
work includes qualified source/fidelity assessment, bounded user-delegated natural
expression admission, trusted gateway ingress and launch, independently observed
delivery/outcome attribution, derived-copy forgetting/retention and the full
longitudinal memory/agenda/adaptation and production lifecycle plan. The remaining
pre-launch/network race is not solved by this read check. No release or deployment
is authorized by these structural tests.
