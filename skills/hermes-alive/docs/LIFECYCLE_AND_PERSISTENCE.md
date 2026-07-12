# Lifecycle and Persistence

## Distribution unit

The complete GitHub repository is the public distribution unit. Supported
installation uses either the root `bootstrap.sh` or Hermes' GitHub skill
transport followed by the lifecycle CLI. A test harness must not pre-populate
the final skill or hook directories.

## Lifecycle commands

```bash
scripts/hermes-alive-lifecycle install
scripts/hermes-alive-lifecycle configure
scripts/hermes-alive-lifecycle verify
scripts/hermes-alive-lifecycle status
scripts/hermes-alive-lifecycle uninstall
scripts/hermes-alive-lifecycle purge
```

- Install/update atomically replaces source and active hook and rolls back when
  validation fails.
- Configure writes only non-secret personalization, automatically detects
  timezone, applies default quiet hours, and emits a structured onboarding result
  for Hermes. It never opens a terminal questionnaire.
- Verify checks manifest integrity, source/hook parity, compilation,
  configuration, and permissions.
- Default uninstall preserves learning/runtime state.
- Purge removes all Hermes Alive-owned state and is destructive.

## Provider ownership

Provider credentials and model configuration belong to Hermes. Hermes Alive
checks readiness but does not launch `hermes setup model` during skill
installation. A missing Provider is a Hermes prerequisite, not a second
Hermes Alive onboarding flow.

Hermes Alive managed configuration must not store API keys or Provider secrets.
Explicit process environment variables take precedence over managed values.

## Zero-touch onboarding contract

Normal installation uses:

```bash
scripts/hermes-alive-lifecycle configure   --non-interactive   --enable   --allow-network-location
```

The command:

1. detects timezone from the Hermes process, local environment, or system;
2. applies default quiet hours `23:00`–`08:00`;
3. prepares an optional unconfirmed district/county-level weather suggestion;
4. leaves weather disabled until confirmation;
5. emits `onboarding_json` for Hermes to interpret.

Hermes may then ask one natural question in the existing chat. Confirmation,
correction, or decline is applied with a second non-interactive lifecycle call.
Installation itself never waits for terminal input.

## Source versus persistent state

Replaceable source:

```text
$HERMES_HOME/skills/hermes/hermes-alive
$HERMES_HOME/hooks/hermes-alive
```

Persistent state:

```text
$HERMES_HOME/hermes_alive_shared
```

A container deployment normally uses `/opt/data` as a mounted persistent Hermes
home. Bare WSL/Linux uses normal local filesystem semantics and does not require
Docker-volume checks.

Install and upgrade may replace source and active hooks but must not delete
persistent user/runtime state. Default uninstall preserves that state; purge is
the explicit destructive path.

## Permissions

Lifecycle-owned metadata and configuration directories are private. Source and
active hooks are readable and not world-writable. Existing learning/runtime
subtrees are not repaired with broad recursive `chmod` operations.

## Production boundary

A changed active hook may require a gateway restart. Production restart,
production source/config changes, and real message delivery require explicit
approval and must never be hidden inside a test or documentation step.
