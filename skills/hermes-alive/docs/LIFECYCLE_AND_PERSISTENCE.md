# Lifecycle and Persistence

## Distribution unit

The complete GitHub repository is the release unit. A standalone `SKILL.md` is
not sufficient. Installation must begin from a repository checkout or supported
Hermes repository transport; test harnesses must not pre-populate final skill or
hook directories.

## Safe default paths

```text
source: $HERMES_HOME/skills/hermes/hermes-alive
hook:   $HERMES_HOME/hooks/hermes-alive
state:  $HERMES_HOME/hermes_alive_shared
```

The shared directory must be a strict child of `HERMES_HOME`. Lifecycle commands
reject unsafe sibling or external paths.

A container deployment normally mounts `HERMES_HOME` persistently. Bare Linux or
WSL uses ordinary filesystem persistence.

## Lifecycle commands

```bash
bash scripts/install.sh

scripts/hermes-alive-lifecycle configure \
  --non-interactive \
  --enable \
  --skip-weather

bash scripts/verify.sh

scripts/hermes-alive-lifecycle status

bash scripts/uninstall.sh
bash scripts/uninstall.sh --purge
```

### Install

Install/update atomically replaces lifecycle-owned source and the active hook.
Validation failure rolls back the previous installation. Running install again
is idempotent.

Success marker:

```text
HERMES_ALIVE_LIFECYCLE_INSTALL_OK
```

### Configure

Configuration is non-interactive. It detects timezone, applies default quiet
hours, writes non-secret managed values, and reports Provider readiness.

Default relevant values:

```text
quality_governor_mode=enforce
quality_topic_expiry_after_unanswered=1
quality_silence_after_unanswered=2
context_flow_max_age_seconds=3600
circadian_mode=shadow
quiet_start=23:00
quiet_end=08:00
```

Success markers:

```text
HERMES_ALIVE_MANAGED_CONFIG_OK
HERMES_ALIVE_ZERO_TOUCH_CONFIG_OK
```

Provider credentials and model selection belong to Hermes. Hermes Alive does not
store secrets or launch a second Provider setup flow.

### Optional weather confirmation

With `--skip-weather`, onboarding completes with weather disabled.

When network-assisted discovery is explicitly allowed, the lifecycle may produce
an unconfirmed suggestion. Hermes may ask one natural question in the existing
chat. Confirmation, correction, or decline is applied with another
non-interactive lifecycle call. Installation never waits for terminal input.

### Verify

Verify checks compilation, manifest presence, source/active-hook parity,
configuration, Provider readiness, and permissions.

Success marker:

```text
HERMES_ALIVE_LIFECYCLE_VERIFY_RESULT=PASS
```

### Uninstall

Default uninstall removes lifecycle-owned source, the active hook, and managed
configuration while preserving shared learning/runtime state.

```text
HERMES_ALIVE_LIFECYCLE_UNINSTALL_OK
shared_state_preserved=true
```

### Purge

Purge removes source, active hooks, stage directories, and all Hermes
Alive-owned shared state.

```text
HERMES_ALIVE_LIFECYCLE_PURGE_OK
shared_state_preserved=false
```

Purge is destructive.

## Persistence contract

Container recreation must preserve the mounted `HERMES_HOME`, including shared
state. Reinstall after uninstall must succeed. Reinstall after purge must create
a clean installation. A final purge must leave no Hermes Alive source, hook,
shared state, or lifecycle stage residue.

## Permissions

Lifecycle metadata and configuration directories are private. Source and active
hooks are readable and not world-writable. Existing learning/runtime subtrees
are not repaired with broad recursive permission changes.

## Production boundary

A changed active hook can require a gateway restart. Production source/config
changes, restart, and real message delivery are separate explicit actions and
must not be hidden inside installation, documentation, or acceptance steps.
