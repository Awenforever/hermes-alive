---
name: hermes-alive
description: "Gateway-native proactive companion with contextual discovery, live quality enforcement, Circadian shadow observation, and reversible lifecycle management."
version: 2.4.2
---

# Hermes Alive — Hermes Installation Contract

## Distribution

Treat the complete GitHub repository as the release unit. `SKILL.md` alone is
not installable. Do not pre-copy source into the final skill or hook directory
before lifecycle installation.

## Preconditions

Before installation:

1. confirm Hermes is installed and `HERMES_HOME` is writable;
2. confirm Hermes has a usable Provider/model;
3. do not request API keys, timezone syntax, quiet-hour syntax, coordinates, or
   internal feature flags in a terminal questionnaire;
4. do not modify Hermes Core, `weixin.py`, production configuration, or gateway
   state as part of installation.

Provider setup remains owned by Hermes. If readiness fails, report the missing
prerequisite and stop; do not launch a second skill-specific Provider flow.

## Paths

Use lifecycle defaults unless the environment explicitly supplies safe paths:

```text
source: $HERMES_HOME/skills/hermes/hermes-alive
hook:   $HERMES_HOME/hooks/hermes-alive
state:  $HERMES_HOME/hermes_alive_shared
```

The shared directory must be a strict child of `HERMES_HOME`.

## Install

From the repository skill root:

```bash
bash scripts/install.sh
```

Require:

```text
HERMES_ALIVE_LIFECYCLE_INSTALL_OK
```

Run the command a second time to verify idempotence. On failure, stop and surface
the lifecycle error; never report success from partial output.

## Configure

Default non-interactive configuration:

```bash
scripts/hermes-alive-lifecycle configure \
  --non-interactive \
  --enable \
  --skip-weather
```

Require:

```text
HERMES_ALIVE_MANAGED_CONFIG_OK
HERMES_ALIVE_ZERO_TOUCH_CONFIG_OK
provider_ready=true
```

Default managed behavior:

```text
quality_governor_mode=enforce
quality_topic_expiry_after_unanswered=1
quality_silence_after_unanswered=2
context_flow_max_age_seconds=3600
circadian_mode=shadow
fixed quiet hours=23:00–08:00
```

Quality enforcement is live when the managed environment exports `enforce`.
Circadian and dynamic sleep/quiet remain shadow/observe-only. The dual-key
isolated delivery enforcement guard is test-only and must not be represented as
production readiness.

Weather is optional. Without confirmed location, keep it disabled. When
network-assisted discovery was explicitly requested, Hermes may ask one natural
question in the existing chat to confirm, correct, or decline the suggested
district/county-level area. Never block installation waiting for that reply.

## Verify

```bash
bash scripts/verify.sh
```

Require:

```text
HERMES_ALIVE_LIFECYCLE_VERIFY_RESULT=PASS
```

Verification must check source and active-hook parity, compilation, manifest,
managed configuration, Provider readiness, and safe permissions.

## Runtime controls

From the installed skill root:

```bash
scripts/hermes-alive-lifecycle status
python3 hooks/alive_control.py status
python3 hooks/alive_control.py disable
python3 hooks/alive_control.py enable
python3 scripts/logs.py --tail 20
```

`alive_control.py test` queues a real delivery request. Do not run it without
explicit approval to send a real message.

Do not manually edit runtime JSON to reset unanswered state. The raw ignored
count is evidence, not a fixed on/off switch.

## Uninstall

Preserve learning/runtime state:

```bash
bash scripts/uninstall.sh
```

Require:

```text
HERMES_ALIVE_LIFECYCLE_UNINSTALL_OK
shared_state_preserved=true
```

Remove all Hermes Alive-owned shared state:

```bash
bash scripts/uninstall.sh --purge
```

Require:

```text
HERMES_ALIVE_LIFECYCLE_PURGE_OK
shared_state_preserved=false
```

`purge` is destructive.

## Safety and release gates

- Never modify Hermes Core or `weixin.py`.
- Never modify or restart production without explicit approval.
- Never send real WeChat messages without explicit approval.
- A failed `SendResult` is not a delivery.
- Model-authored messages must retain the routed model in footer metadata.
- Run complete regression, fresh-container lifecycle, persistence, uninstall,
  reinstall, and purge gates before repository release.
- Isolated acceptance is not final production completion.
- Complete repository transport, real GitHub URL installation, spare-WeChat E2E,
  controlled production deployment, restart persistence, and stability
  observation remain separate gates.
