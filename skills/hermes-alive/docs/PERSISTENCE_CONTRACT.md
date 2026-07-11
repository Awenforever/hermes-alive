# Persistence Contract

Skill: `hermes-alive`

## Principle

This skill must be environment-aware.

- Bare WSL/Linux: no Docker volume requirement. Use normal local filesystem semantics.
- Docker/container runtime: `HERMES_HOME` must point to the persistent Hermes data root, normally `/opt/data`, and `/opt/data` should be a mounted volume or bind mount.

## Source vs user/runtime data

Source is replaceable and may be reinstalled or upgraded:

```text
$HERMES_HOME/skills/...
$HERMES_HOME/hooks/...
```

User/runtime state must not be stored inside source and must survive container rebuilds.

Likely state for this skill:

```text
$HERMES_HOME/hermes_alive_shared
$HERMES_HOME/hermes_alive_shared/locks
$HERMES_HOME/.env HERMES_PROACTIVE_* settings
$HERMES_HOME/hooks/hermes-alive runtime cache/state if any
```

## Install/upgrade rule

Install and upgrade may replace the source skill and active hook, but must not delete user/runtime state.

## Uninstall rule

Uninstall removes the active hook and installed source only. It must preserve user/runtime state by default.

Deleting user/runtime data requires an explicit destructive confirmation such as:

```text
DELETE_USER_DATA
```

## Verification

Run:

```bash
python3 scripts/verify-persistence.py
```

In Docker, this verifies that `HERMES_HOME` exists and that `/opt/data` looks like a mounted persistent data root. In bare WSL/Linux, it only verifies local paths and reports that Docker persistence is not required.
