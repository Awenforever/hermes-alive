# ADR-0022: Action authorization is short-lived and revalidated

Status: accepted for the shadow kernel

## Context

A model selection is an intent, not permission to act. Time can pass between
framing, selection and execution: the user may become unavailable, an agenda
item may close, evidence may expire, a newer exploration gate may supersede the
old one, or the requested Hermes capability may not match the side effect.
Treating the earlier selection as a standing permit would turn stale cognition
into an external action.

## Decision

The kernel has a separate send-time authorizer. It accepts one exact validated
selection and rechecks the latest selection, latest exploration gate, current
deterministic policy, evidence validity, active agenda, subject and sensitivity,
requested Hermes capability and authority provenance.

An observed opportunity is not user delegation. `user_delegated` actions need
an active agenda rooted in explicit user authority. Migrated authority and
`system_critical` remain fail-closed until their own provenance schemas exist;
Hermes core remains responsible for critical lifecycle notices.
`user_confirmed` actions need a later inbound confirmation
that explicitly names the selected event. An arbitrary user message cannot be
used as confirmation.

A successful decision creates only a structural authorization receipt. The
permit expires in at most 60 seconds, contains no candidate body and performs
no channel or tool operation. Reusing its operation ID is idempotent, but an
expired receipt is returned as unauthorized rather than revived.

## Consequences

- A model, opportunity generator or old selection cannot grant itself durable
  external authority.
- Quiet-window, risk and capability changes take effect immediately before an
  action boundary.
- Selection quality and authorization policy remain separately inspectable.
- A future executor must consume an unexpired receipt, recheck it atomically
  against idempotent attempt creation, and publish an observed result. This ADR
  does not authorize connecting the shadow kernel to production delivery.
