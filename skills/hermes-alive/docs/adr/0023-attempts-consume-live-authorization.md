# ADR-0023: Action attempts consume live authorization

Status: accepted for the shadow kernel

## Context

ADR-0022 introduced a short-lived send-time authorization receipt, but the
existing outcome projection still allowed callers to create `action.attempted`
directly from a model selection. That left a bypass around the new authority
boundary. Recovery also projected outcomes before exploration, while a valid
selection depends on an exploration receipt; rebuilding empty projections
could therefore reject a chain that had been valid online.

## Decision

Every action attempt must cite one prior `action.authorization_evaluated`
event produced by the Alive authorizer. The attempt projection independently
checks exact selection, candidate, capability, subject, sensitivity, causal
ordering, maximum 60-second validity, receipt expiry, latest validated
selection, latest exploration gate and any active agenda reference. Missing,
forged, mismatched, superseded or expired receipts fail closed.

Receipts carry an installation-local HMAC over their canonical structural
payload. The authenticator is verified both when an idempotent authorization is
reopened and when an attempt consumes it. Merely copying the expected
`source`/`actor` strings cannot forge authority.

The attempt remains a durable intent-to-execute record; it performs no external
operation. Delivery or tool adapters must still execute through Hermes and
publish a separate observed outcome.

Recovery is split into dependency order:

`agenda → deliberation frames → exploration → deliberation selections → outcomes`

A dedicated frame checkpoint breaks the former replay cycle without weakening
selection validation.

## Consequences

- There is no supported selection-to-attempt shortcut.
- Authorization integrity depends on the managed installation identity key;
  migration and backup must preserve that key with the encrypted kernel state.
- Authorization expiry semantics are identical at lookup and consumption.
- A state change between authorization and consumption can invalidate the
  attempt before an adapter receives work.
- Existing shadow attempts without authorization no longer qualify on rebuild;
  they are historical pre-contract evidence, not executable state.
- Actual delivery, crash-safe dispatch leasing and transport receipts remain a
  later boundary and are not enabled by this ADR.
