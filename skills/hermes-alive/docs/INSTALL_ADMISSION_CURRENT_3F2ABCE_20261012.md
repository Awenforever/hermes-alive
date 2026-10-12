# Current audited-source installed-runtime verification

Status: r5 installed-runtime lifecycle passed; overall production acceptance incomplete

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

## 2026-10-13 — Cached base and standard core preparation

- Test-only base build completed with exit zero. Image ID:
  `sha256:5cb2abffe8c4229ba1be65f0e61ec7393d17ba27dffc8066a908b7c2a52df063`.
  Tag `hermes-alive-admission-base:20261012-v1`; recipe is
  `tests/fixtures/install-admission-base.Dockerfile`. No source/profile/key is
  baked in. The base prepares OS tooling and uv, not Hermes-managed dependencies.
- r2 container `alive-installed-20261013-r2` has terminal exit 1. Its exact
  argument vector had no CR. Imported core location was correct, but a bare
  Python carrier lacked `ruamel.yaml` before CLI dependency activation. No
  plugin admission occurred; retained `admission-r2.log` is prerequisite evidence.
- r3 container `alive-installed-20261013-r3` has terminal exit 1. The official
  `pm install --extra all` path prepared some tools but refused venv sync because
  standard node/npm/ffmpeg/ripgrep tools were absent. This source checkout was
  not yet a complete installed Hermes. Retained `admission-r3.log`; do not label
  this a plugin regression or bypass the guard with raw pip.
- r4 uses the normal public `pm install` first, omitting only the two explicitly
  optional browser/CUA tools, then runs the unchanged admission fixture. Required
  tools and default Python extras remain Hermes-owned. No dependency lock is
  changed. Already downloaded tools are reused under the owned scratch home.
- r4 container `alive-installed-20261013-r4`, started
  `2026-10-12T17:47:40.781315002Z`, ultimately exited 1. Standard core preparation
  succeeded, including required tools and default venv. The subsequent fixture
  still called bare carrier Python rather than that managed interpreter and
  failed on YAML import before plugin admission. Reuse the completed core,
  not a repeated install or a manually patched carrier.
- Its home is `/test/managed-owner` within the owned scratch mount; source/core
  archives remain the original immutable inputs. No production data is mounted.
- Retained log: `admission-r4.log`; log-follow handle 71068 is an observer, not
  the task. Keep the stopped test containers until their exit/evidence is
  recorded; do not infer success from a running container's default exit value.
- No automatic restart on timeout; revalidate actual state before continuing.

## 2026-10-13 — r5 terminal installed-runtime result

- Asked actual `pm.environments.selected_venv` and `venv_command` for the
  committed core environment, then ran the unchanged fixture in that runtime.
  No additional core preparation or raw dependency install occurred.
- Container `alive-installed-20261013-r5` started
  `2026-10-12T17:54:04.077016424Z`, finished
  `2026-10-12T17:57:54.006214203Z`, running false, exit zero. Collected terminal
  log-follower handle 19133; retained `admission-r5.log` contains
  `HERMES_ALIVE_INSTALL_ADMISSION_OK` and durable-state create/check results.
- Actual public package admission and loaded `alive status` succeeded. Runtime
  install twice, same-revision package refresh, runtime uninstall, package removal
  and reinstall passed. The original synthetic journal/checkpoint, identity and
  content keys, and decryptable private content survived every checked transition.
  The runner selected the plugin-enabled managed generation for subsequent steps.
- This is exact audited-source, NAS/Linux Docker, local Git-fixture package
  qualification. It is not a published-GitHub install, previous-release upgrade,
  generated console-entry pass, real authenticated-user migration, live gateway
  delivery or usefulness result. No gateway ran; proactive enabled remained false.
- The reusable tooling image and owned managed store now exist for subsequent
  bounded tests. Keep their identity/evidence; do not redownload core dependencies
  or silently use the carrier interpreter on continuation. Stopped containers
  remain available for exit-code verification until explicit owned cleanup.

## Remaining scope

Generated installed console entry, real external receipts, live authorization
migration, semantic shadow/human calibration and longitudinal usefulness remain
separate gates. Production `hermes-v0213-gateway` was confirmed running with
unchanged start time `2026-10-11T07:43:25.630569081Z`. Nothing has been deployed to it.
