<div align="center">

# Hermes Alive

**A gateway-native proactive companion for Hermes and WeChat.**

Context-aware conversation, carefully timed proactive messages, external discovery,
interest learning, truthful model attribution, and a reversible lifecycle.

[中文说明](README_CN.md) · [Architecture](docs/ARCHITECTURE.md) · [Testing](docs/TESTING_AND_ACCEPTANCE.md)

</div>

## What it changes

Hermes Alive adds a proactive layer to Hermes without replacing Hermes Core or
the WeChat adapter. After installation, Hermes can:

- remember bounded recent context and avoid interrupting active work;
- start a new topic when there is real value instead of repeating an old prompt;
- collect several discovery candidates and share them one at a time without
  replaying the same URL or topic;
- adapt wording, interests, and bubble count to the conversation;
- reject repeated, unsupported, or pressure-inducing proactive drafts before
  delivery;
- preserve the real routed model in footer metadata;
- keep replaceable source separate from persistent user/runtime state.

Circadian state is currently learned and observed in shadow mode. Fixed quiet
hours remain authoritative. Dynamic sleep/quiet enforcement is not presented as
production-ready.

## Quick start

From the complete repository checkout:

```bash
cd skills/hermes-alive

bash scripts/install.sh

scripts/hermes-alive-lifecycle configure \
  --non-interactive \
  --enable \
  --skip-weather

bash scripts/verify.sh
```

A successful run prints:

```text
HERMES_ALIVE_LIFECYCLE_INSTALL_OK
HERMES_ALIVE_ZERO_TOUCH_CONFIG_OK
HERMES_ALIVE_LIFECYCLE_VERIFY_RESULT=PASS
```

The Provider and model remain owned by Hermes. Hermes Alive checks readiness but
does not open a second Provider questionnaire or store API keys.

## First run

The non-interactive configuration flow:

1. detects the local timezone;
2. applies default quiet hours `23:00`–`08:00`;
3. enables the live proactive quality governor;
4. keeps Circadian in `shadow`;
5. leaves weather disabled when `--skip-weather` is used;
6. writes managed, non-secret configuration under the shared state directory.

Weather is optional. When network-assisted location discovery is explicitly
allowed, Hermes may ask one natural chat question to confirm, correct, or decline
the suggested area. Installation never waits for terminal input.

## Main capabilities

### Context-aware proactive conversation

Hermes Alive checks current activity, recent context, cooldown, interruption
policy, and delivery evidence before composing and again before each send. Bubble
count is planned from semantic acts and stays within 1–5; it is not fixed.

### Discovery without replay

A discovery collection may contain multiple ranked candidates. One proactive
share consumes one eligible candidate. Later ticks reuse the cache but select a
different unseen candidate. Delivered, reserved, or duplicate topics are
suppressed. A topic may re-enter only when a verifiable material-update
fingerprint changes.

### Quality enforcement

The managed lifecycle defaults the proactive quality governor to `enforce`.
It can block repeated openings, semantic duplicates, unsupported task-status
claims, repeated affect from one silence episode, and misleading weather
perspective. `off` and `shadow` remain explicit configuration options.

### Interest and voice adaptation

Interest changes are attributable and reversible. Explicit feedback is stronger
than weak conversational signals, and sensitive identity traits are not inferred.
Voice and style adaptation remain bounded by safety and delivery constraints.

### Truthful model attribution

Model-authored messages retain the routed model identity through delivery.
Deterministic lifecycle, control, and system payloads use Hermes system metadata.

## Environment

Hermes Alive expects:

- a working Hermes installation and configured Provider;
- a writable `HERMES_HOME`;
- Python available through the Hermes runtime;
- a supported gateway hook environment.

Docker is optional. In containers, mount `HERMES_HOME` persistently. Bare Linux
or WSL uses normal filesystem persistence.

## Paths and data

Default lifecycle paths are:

```text
$HERMES_HOME/skills/hermes/hermes-alive
$HERMES_HOME/hooks/hermes-alive
$HERMES_HOME/hermes_alive_shared
```

The shared directory must be a child of `HERMES_HOME`.

Persistent data may include managed configuration, bounded context, interest and
voice profiles, discovery evidence, topic-delivery hashes, proactive logs, and
Circadian observability. Provider credentials remain in Hermes configuration.

See [Data and Privacy](docs/DATA_AND_PRIVACY.md).

## Status and verification

From the installed skill root:

```bash
scripts/hermes-alive-lifecycle status
bash scripts/verify.sh
python3 hooks/alive_control.py status
python3 scripts/logs.py --tail 20
```

To disable or re-enable proactive delivery without deleting data:

```bash
python3 hooks/alive_control.py disable
python3 hooks/alive_control.py enable
```

Do not edit runtime JSON files to “reset” silence. Unanswered counts are evidence,
not a fixed on/off switch. Use status, logs, and the documented control surface.

See [Proactive silence troubleshooting](references/troubleshooting-silent-mode.md).

## Uninstall and purge

Default uninstall removes installed source, the active hook, and managed
configuration while preserving learning/runtime state:

```bash
bash scripts/uninstall.sh
```

To remove all Hermes Alive-owned shared state:

```bash
bash scripts/uninstall.sh --purge
```

`purge` is destructive. Production restarts, production source/config changes,
and real message delivery remain separate explicit operations.

## Current validation boundary

The current source has passed isolated hardening, complete regression, fresh
install, idempotent install, persistence, uninstall, reinstall, purge, and
zero-residue lifecycle acceptance. The remaining release path is documented in
[Testing and Acceptance](docs/TESTING_AND_ACCEPTANCE.md), including complete
repository transport, real GitHub URL installation, spare-WeChat E2E, and
controlled production acceptance.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Runtime Policies](docs/RUNTIME_POLICIES.md)
- [Lifecycle and Persistence](docs/LIFECYCLE_AND_PERSISTENCE.md)
- [Data and Privacy](docs/DATA_AND_PRIVACY.md)
- [Testing and Acceptance](docs/TESTING_AND_ACCEPTANCE.md)
- [Discovery Development](docs/DISCOVERY_DEVELOPMENT.md)
- [Test Guide](tests/TESTING.md)

## License

See [LICENSE](LICENSE).
