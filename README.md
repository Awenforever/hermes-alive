<div align="center">

# Hermes Alive

**A gateway-native proactive companion for Hermes Agent.**

Presence, personality, memory, and circadian rhythm—without turning every silence into a notification.

![version](https://img.shields.io/badge/version-2.4.3-blue)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)
![Hermes](https://img.shields.io/badge/Hermes-gateway--native-6f42c1)
![license](https://img.shields.io/badge/license-MIT-green)

[中文](README_CN.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md)

</div>

---

## What it is

[Hermes Alive](https://github.com/Awenforever/hermes-alive) adds a proactive interaction layer to [Hermes Agent](https://github.com/NousResearch/hermes-agent). It runs with the Hermes gateway, follows recent WeChat context, and occasionally starts a conversation when the timing and content are appropriate.

> **Presence without obligation.** Hermes may notice, remember, react, go quiet, sleep, wake, and speak first—but it should never demand attention.

Hermes Alive uses the Provider, model configuration, gateway, and WeChat adapter already managed by Hermes. It does not replace Hermes or maintain a separate credential system.

## Core capabilities

| Capability | What it does |
|---|---|
| Context-aware initiative | Avoids interrupting active work, pending replies, or fresh conversations. |
| Personality and relationship state | Adapts tone and initiative through bounded, reversible learning. |
| Circadian rhythm | Models sleep, wakefulness, delayed sleep, sleep debt, and recovery. |
| Interruption and quality policy | Blocks repetition, pressure, unsupported task claims, and unsafe proactive drafts. |
| Discovery | Finds and rotates potentially useful external content without repeatedly sharing the same topic. |
| Dream consolidation | Optionally turns high-confidence conversation evidence into bounded memory updates. |
| Traceable delivery | Preserves the actual routed model and links decisions through a shared `tick_id`. |
| Safe lifecycle | Supports atomic installation, verification, rollback, state-preserving uninstall, and purge. |

## How it works

```text
Hermes gateway
  → recent context and activity checks
  → circadian and interruption policy
  → personality, memory, and optional discovery
  → model composition
  → quality and duplicate checks
  → WeChat delivery
```

System and safety messages keep their own priority and are not treated as ordinary social interruptions.

## Quick start

Requirements:

- a working Hermes installation;
- Python 3.11 or later;
- a Provider/model configured in Hermes;
- a writable `HERMES_HOME` (normally `/opt/data`).

Install from the complete repository:

```bash
git clone --depth 1 \
  https://github.com/Awenforever/hermes-alive.git \
  /tmp/hermes-alive

cd /tmp/hermes-alive
HERMES_HOME=/opt/data bash scripts/bootstrap.sh
```

The bootstrap installs the source skill and active gateway hook, writes non-secret defaults, and runs verification. It does not restart the gateway. Restart Hermes with the normal procedure for your deployment after reviewing the result.

## Configure and operate

```bash
export HERMES_HOME=/opt/data
LIFECYCLE="$HERMES_HOME/skills/hermes/hermes-alive/scripts/hermes-alive-lifecycle"

"$LIFECYCLE" configure
"$LIFECYCLE" verify
"$LIFECYCLE" status
```

Provider credentials remain in Hermes. If Hermes has no usable model, configure it with:

```bash
/opt/hermes/.venv/bin/hermes setup model
```

Pause or resume proactive delivery without uninstalling:

```bash
python3 "$HERMES_HOME/hooks/hermes-alive/alive_control.py" disable
python3 "$HERMES_HOME/hooks/hermes-alive/alive_control.py" enable
python3 "$HERMES_HOME/hooks/hermes-alive/alive_control.py" status
```

## Data and removal

```text
$HERMES_HOME/skills/hermes/hermes-alive  installed source
$HERMES_HOME/hooks/hermes-alive          active gateway hook
$HERMES_HOME/hermes_alive_shared         configuration and persistent state
```

Provider secrets stay in Hermes configuration. Hermes Alive does not modify Hermes Core or `weixin.py`.

Default uninstall removes the installed source, hook, and managed configuration while preserving learned and runtime state:

```bash
bash "$HERMES_HOME/skills/hermes/hermes-alive/scripts/uninstall.sh"
```

To remove all Hermes Alive state as well:

```bash
bash "$HERMES_HOME/skills/hermes/hermes-alive/scripts/uninstall.sh" --purge
```

`--purge` is destructive. Production restarts and real-message tests should always be explicit operational decisions.

## Documentation

- [Architecture](skills/hermes-alive/docs/ARCHITECTURE.md)
- [Runtime policies](skills/hermes-alive/docs/RUNTIME_POLICIES.md)
- [Lifecycle and persistence](skills/hermes-alive/docs/LIFECYCLE_AND_PERSISTENCE.md)
- [Data and privacy](skills/hermes-alive/docs/DATA_AND_PRIVACY.md)
- [Testing](skills/hermes-alive/tests/TESTING.md)

## License

[MIT](LICENSE)
