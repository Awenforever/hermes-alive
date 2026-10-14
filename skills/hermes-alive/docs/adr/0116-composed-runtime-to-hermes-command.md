# ADR 0116 — Composed runtime to actual Hermes command, local sink only

Date: 2026-10-14

## Implementation

The preparation runtime now exposes `execute_prepared_with_cli` for the exact
prepared action attempt and its acquired lease. It verifies owner and canonical
attempt/authorization/selection identity before delegating to the existing
single-start CLI execution seam. Host process/profile/parser callbacks remain
trusted operator capabilities, not model-selected code or inferred permission.
Actual outbox checks still own permit freshness, revocation, content binding,
cadence and consumed-start recovery. This is an action-intent ledger, not a
replacement Weixin FIFO. Hermes' channel transport owns platform delivery.

The method returns a command observation, not a delivery success. An exception
after consuming a start is unresolved and must not automatically resend. Neither
CLI reports nor local fixture effects become user satisfaction or learning.

## Composed host exercise

New `run_alive_kernel_host_runtime_chain.py` composes discovery, model planning,
natural expression/review, explicit synthetic expression delegation, send-time
authorization, one action attempt and the actual Hermes send command. It reuses
the existing isolated host command harness with an injected runtime preparer;
the old exact-confirmation harness remains covered independently.

Four actual command paths are checked: success, error/rejection, partial report
and cron-owned skip. Only success/partial produce one local fixture effect.
Reported text exactly matches the retained selected expression, including its
source URL; target exactly matches the operator-qualified synthetic route.
Foreign attempt leases are refused before consuming a start. A second execution
of the same lease never launches the command twice. The model planning and
expression operations are synthetic and do not repeat at the transport boundary.

The diagnostic source review deliberately records uncertain factual support;
it is not converted into factuality qualification or permission. Synthetic user
delegation, rather than the review, supplies the separately bounded send scope.
The live authenticated onboarding/grant path still needs implementation.

## Evidence and scope

Windows send-preparation regression passes. Actual Hermes command composition is
qualified here only on isolated Linux, not Windows production or a fresh install.
`alive-host-runtime-chain-offline-20261014-r2` exits 0 for all four composed modes
and all four old host-expression regression modes. It uses network-disabled,
read-only scratch mounts, 1 CPU/2 GiB/256 PIDs. Child network/process barriers are
verified; all sinks and profiles are synthetic. The core export is the previously
qualified pinned `/test/core`, not a claim of testing every latest upstream file.

Dependency snapshot: ADR-0115 source plus these exact files:

- preparation runtime SHA-256: `db56578612ff20973afb8b8730073593405093f9ccb3354164b7e22740a4ba30`
- composed host test SHA-256: `7b03fcaa3b32292107f38d1015a331a151da493ddae31152db814110132e94e0`
- host-expression harness SHA-256: `66c095cee19a69ff62c402936b592f4b8837d1cf904ffc82d01218bd4d14cbf7`

This is stronger than a mocked launcher but still does not prove external Weixin
delivery, canonical wire message IDs, startup watcher activation or useful
longitudinal behavior. There are zero real model calls and zero real channel
sends. Production config, process start time, auth state and other plugins remain
unchanged. Next connect trustworthy delivery/history and feedback attribution,
authenticated opt-in controls and bounded scheduling; then qualify actual model
quality, real channel canary, portable installation/migration and rollback.
