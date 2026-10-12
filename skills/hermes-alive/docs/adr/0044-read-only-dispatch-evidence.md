# ADR-0044: Read-only canonical dispatch evidence verification

Status: accepted as verification foundation; outcome integration pending

Amended by ADR-0045 for outcome admission/read integration.

## Finding and decision

Generic outcome admission and feedback-derived projections do not yet prove
the signed transport/task receipt chain. Same-user chronological evidence is
insufficient for a delivery result, just as it was insufficient for feedback.

Expose a `DispatchEvidenceVerifier` with no enqueue, dispatch or schema-setup
capability. It receives the host journal and existing identity protector.
Reuse the canonical authenticated-start/result and structural predicates from
`DispatchOutbox`, not a second independently evolving implementation.
The small facade binds exactly those read-only predicates and the deterministic
start identity function; do not inherit the action-capable outbox class.

The caller must supply an already validated action attempt. The verifier checks
signed result and start payloads, exact attempt/idempotency/capability binding,
subject/sensitivity, sequence/time ordering, deterministic start identity and
lease generation. Policy identity comes from the attempt's authorization, not
from the result's own claim. Reject boolean generations despite Python's
`bool`/`int` subtype relation. An optional observation cutoff prevents future
receipts from entering a past evaluation.

Receipt verification does not grant action authority, prove factual usefulness
or imply that a user saw the message. It does not itself validate the attempt's
authorization. Construction performs no schema initialization or key creation.

## Evidence and required next step

Tests cover a signed compatible chain, invalid signature, foreign subject,
wrong attempt/idempotency/capability/start/generation/outcome and a future
observation cutoff. They also assert that verification created no operational
tables and exposes no enqueue/dispatch API. The existing recovery regression
checks the verifier against its actual authenticated start/result fixture,
using the authorization and retry-generation logic rather than only a minimal
unit fixture.

Next, integrate this check into generic outcome admission, cached outcome
reads and dependent non-user evidence paths, replacing unsigned positive test
fixtures with authentic host receipts. Until that change is tested, the
transport gap remains open and the kernel cannot enter live qualification.

On 2026-10-12 verifier and authenticated recovery tests passed on Windows and
in a disposable production-image container with no networking or production
data access. The existing production gateway was not updated or restarted.
