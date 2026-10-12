# ADR-0055: Process reports are not terminal outcomes

Status: implemented for observation recording; live executor still disconnected

## Decision

A public `hermes send` process result is useful execution evidence but its
success flag/exit status alone cannot justify a terminal delivery outcome.
Keep this weaker evidence rather than discarding it or promoting it into a
reward. Platform acknowledgement, recipient attention and benefit are separate.

`transport_receipts.py` classifies reports as success/error/partial/skip
**reported**, or unknown. It requires strict booleans, bounds input bytes,
rejects duplicate JSON fields and non-finite values, and preserves valid native
Windows crash exit codes as unknown observations. Additional response fields
are allowed but cannot establish `external_delivery_proven`. Error text,
message IDs, links and arbitrary payload fields are never copied to the journal.

`DispatchOutbox.record_cli_observation` binds one final process report to a
channel-send execution with an authenticated start, matching outbox generation
and lease token. It records `transport.cli.observed`, a typed summary and keyed
stdout fingerprint. A dedicated local integrity authenticator protects the
observation; it is not an independent Hermes host signature or proof that a
process actually ran. Trusted executor integration remains required.

The method never changes outbox state, calls a transport, authorizes another
send or acknowledges the attempt. Outcome and dispatch-result projections do
not treat this event as `delivery.succeeded`, `delivery.failed` or task
completion. `acknowledge` rejects an observation event. Identical replay returns
the existing observation; different stdout/report evidence for the same start
conflicts instead of overwriting it.

## Scope and unresolved work

- Recovery tests use real synthetic authorization, lease and start fixtures;
  they are not production route/provider qualification.
- Current upstream's six local-platform command results also run through this
  classifier. The command-to-classifier and lease-to-journal tests are separate,
  not a complete authorized subprocess-to-delivery bridge.
- Only a still-started matching lease can record through this method. A
  reconciled uncertain/retired execution cannot be relabelled by a new owner.
  Forensic late-receipt recovery needs an explicit separate mechanism.
- Error or partial reports are not evidence of zero external effects. Pending
  reconciliation must retain uncertainty; do not retry on failure status alone.
- The live executor, profile-bound command invocation, qualified platform
  receipts, crash/timeout recovery and human usefulness remain incomplete.

Production remains unchanged; no live sender is enabled by this module.
