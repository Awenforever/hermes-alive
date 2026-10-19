# ADR 0184: Composed native host, feedback, restart and forgetting proof

Date: 2026-10-19
Status: controlled integration passed; packaging qualification pending

## Problem

Separate component tests and a silent host cycle do not establish that generation,
tentative feedback, durable recovery and forgetting cooperate through real Core.
Do not add another scheduler or infer production readiness from isolated hooks.

## Decision

Add `tests/probe_alive_native_living_cycle.py` and its HTTP-intercepting bootstrap.
Run the existing native worker and host runtime against an explicit official Core
checkout and a managed interpreter. Use only synthetic credentials, public-source
fixtures and clearly synthetic historical delivery/feedback records. Disable the
physical network and never invoke transport. Existing synthetic historical action
records are counted before and after; they are not claims of actual delivery.

The probe exercises an enabled shadow cycle, feedback interpretation and complete
message preparation. Inject a crash after the inner cycle completes but before
the durable host cycle closes. Reopen the journal and resume the same cycle.
Erase the original feedback content, update the public source and run a new cycle.
Assert the forgotten interpretation and original quote no longer enter cognition.
Advisory feedback must not automatically become permanent profile memory/weights.

## Observed result

Against official Core snapshot 548e66f, the network-disabled focused run passed:
15 intercepted model protocol calls, one feedback interpretation, zero additional
inference on restart, no forgotten feedback in the next generation, no additional
permanent profile writes, action attempts or physical sends. Native worker scratch
directories and pending calls are empty at the asserted boundaries.

All model answers are controlled fixtures. This proves real Core protocol and
composition mechanics, not actual model intelligence, semantic correctness,
production installation, background scheduling or successful channel delivery.
It earns no fresh real-model acceptance round. Host embedding/read leases, useful
fresh recommendations, durable noisy-memory behavior and the full lifecycle and
production acceptance matrix remain open.

## Reproduction and scope

Use a managed Hermes interpreter with the Core dependencies, and an explicit
read-only Core checkout:

```text
python -B tests/probe_alive_native_living_cycle.py --core <core-checkout> --output <new-private-output>
```

The output directory must not already exist. Run in an isolated container with no
network, a writable private output mount, read-only source/Core and disposable
worker space. The portable source-only CI does not supply Core; its success must
not be described as running this integration probe. Retain the separate actual
integration result and source identity. No new public runtime path or production
configuration change is introduced by this decision.
