# Hermes Alive

Complete GitHub distribution repository for the Hermes Alive gateway skill.

## AI/Hermes installation

The repository is self-installing. From a fresh Hermes container:

```bash
git clone --depth 1 https://github.com/Awenforever/hermes-alive.git /tmp/hermes-alive
bash /tmp/hermes-alive/bootstrap.sh --hermes-home /opt/data
```

Hermes may alternatively use its official GitHub skill transport:

```bash
/opt/hermes/.venv/bin/hermes skills install \
  Awenforever/hermes-alive/skills/hermes-alive \
  --category hermes --yes

cd /opt/data/skills/hermes/hermes-alive
scripts/hermes-alive-lifecycle install
```

The bootstrap installs the source skill and active hook atomically, compiles
all Python modules, creates a manifest, normalizes permissions, and preserves
runtime learning state during upgrades.

Provider credentials are never stored by this repository. When no model is
configured, run:

```bash
/opt/hermes/.venv/bin/hermes setup model
```

Production replacement is not part of installation acceptance. It is
considered only after fresh-container matrix, stress, real spare-Weixin and
clean-uninstall tests pass.

## Phase H test suites

Markers: `HERMES_ALIVE_MATRIX_SUITE_V1` and `HERMES_ALIVE_STRESS_SUITE_V1`.

```bash
python3 skills/hermes-alive/tests/run_matrix.py
python3 skills/hermes-alive/tests/run_stress.py
```

Final acceptance must use the default full stress scale. Reduced scale is developer smoke only.

## Lifecycle commands

```bash
LIFECYCLE=/opt/data/skills/hermes/hermes-alive/scripts/hermes-alive-lifecycle

"$LIFECYCLE" configure --provider-check-only
"$LIFECYCLE" configure
"$LIFECYCLE" verify
"$LIFECYCLE" status
"$LIFECYCLE" uninstall
"$LIFECYCLE" purge
```

Default uninstall preserves learning/runtime state. `purge` removes all Hermes
Alive shared state. Production restart and real-message testing require
explicit approval.

## Public repository contract

Public documentation uses only the complete GitHub repository, root bootstrap
and lifecycle CLI. It does not depend on unpublished branches, manual hook
copying or legacy deployment instructions.

Marker: `HERMES_ALIVE_PUBLIC_DOCUMENTATION_CONTRACT_V1`.
