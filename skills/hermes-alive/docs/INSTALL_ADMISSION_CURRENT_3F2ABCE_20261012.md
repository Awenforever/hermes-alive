# Current audited-source installed-runtime verification

Status: terminated before admission; harness line-ending correction verified

## Immutable inputs

- Alive source revision: `fb11b19`, development branch, package version 2.9.8.
- Audited Hermes source: `3f2abce7f468cf194bb7f9ff9c6a033b075d834c`.
- Git archives, not working-tree copies. Local and NAS SHA-256 match:
  - Alive: `a1cec348ac7d5016ef20c87baaebc0314508813444905ef452f81e018b3d2353`.
  - Hermes: `2107c7cc2129af56f794b2a79c324c0c2954484fa5f0f51e2d3cc3e3fb395c64`.

## Isolated job and recovery pointers

- NAS test container: `alive-installed-20261012-rjbqnaid`.
- Started `2026-10-12T15:17:05.54811026Z`; foreground handle later returned exit 1
  and the auto-removed container is authoritatively absent.
- Owned scratch: `/tmp/hermes-alive-installed-RJbQNAiD`.
- Durable synthetic job output: `admission.log` in that scratch directory.
- Local foreground execution handle: 46250; log follower handle: 14632.
  Handles are recovery pointers, not evidence that a resumed job is still live.
- Limits: one CPU, 2 GiB memory, 256 processes. Fresh `python:3.13-slim` container;
  only the owned scratch is mounted, never production data or authentication.
- Dependency network uses the existing NAS proxy at loopback port 17898 via
  test-only host networking. No existing container/network/proxy configuration
  changes. Only base bootstrap tooling is installed with pip; Hermes owns its
  application dependency admission and selected runtime.

The attached Docker run performs base tooling setup, then the existing opt-in
`run_alive_install_admission.py --allow-dependency-install` on these inputs.
It verifies admitted runtime readiness and encrypted synthetic state across
repeated install, package refresh, removal and reinstall. No gateway starts;
Alive remains disabled. This is current audited-source qualification, not a
claim that this commit remains upstream latest indefinitely.

Base Debian tooling and uv 0.13.0 installation completed. The admission runner
then rejected a visually correct flag containing a trailing carriage return
from the PowerShell/native SSH script boundary. No plugin admission occurred;
this is a harness failure, not installation or lifecycle evidence. A small
network-disabled Docker probe verified that remote `tr -d "\\r" | sh -s`
preserves the flag exactly. Apply this correction before any fresh job.
No `HERMES_ALIVE_INSTALL_ADMISSION_OK` was observed. Preserve that distinction.
The log follower completed too; its exit code cannot prove job success.
Because the container uses `--rm`, disappearance alone cannot prove success either.
The original attempt is terminal, not an observation timeout. Keep its retained
log as failure evidence; a new corrected attempt needs its own identity. Prefer
a reusable test-only base image so successful tooling setup is not repeatedly
downloaded. Never treat a missing container alone as a success or failure proof.

After terminal evidence, record actual results here and clean only these verified
owned archives/scratch after preserving needed evidence. Do not delete other
historical `/tmp/alive*` directories based on their names.

## Remaining scope

Generated installed console entry, real external receipts, live authorization
migration, semantic shadow/human calibration and longitudinal usefulness remain
separate gates. Production `hermes-v0213-gateway` was confirmed running with
unchanged start time `2026-10-11T07:43:25.630569081Z`. Nothing has been deployed to it.
