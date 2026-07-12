---
name: hermes-alive
description: "Hermes Alive — a gateway-native proactive companion for WeChat with managed lifecycle, contextual personality, circadian shadow decisions, quality safeguards, and clean uninstall."
version: 2.4.0
---

# Hermes Alive

Hermes Alive is distributed as the complete GitHub repository
`Awenforever/hermes-alive`. A standalone `SKILL.md` is not a complete release.

## Supported installation paths

### Repository bootstrap

```bash
git clone --depth 1 https://github.com/Awenforever/hermes-alive.git /tmp/hermes-alive
bash /tmp/hermes-alive/bootstrap.sh --hermes-home /opt/data
```

### Hermes GitHub skill transport

```bash
/opt/hermes/.venv/bin/hermes skills install \
  Awenforever/hermes-alive/skills/hermes-alive \
  --category hermes --yes

cd /opt/data/skills/hermes/hermes-alive
scripts/hermes-alive-lifecycle install
```

The installer owns final source and hook placement. Test harnesses must not
pre-copy files into `/opt/data/skills` or `/opt/data/hooks` before installation.

## Provider and personalization

Provider credentials and model selection remain owned by Hermes. Hermes Alive
stores only non-secret personalization.

```bash
LIFECYCLE=/opt/data/skills/hermes/hermes-alive/scripts/hermes-alive-lifecycle

"$LIFECYCLE" configure --provider-check-only
/opt/hermes/.venv/bin/hermes setup model
"$LIFECYCLE" configure
"$LIFECYCLE" verify
"$LIFECYCLE" status
```

Explicit process environment variables override managed values. Never place
API keys, tokens, or private chat credentials in the repository.

## Runtime responsibilities

Hermes Alive installs a gateway hook that can:

- maintain bounded conversation context and activity state;
- evolve a per-user voice profile and interest profile;
- discover external content through configured sources;
- compose proactive messages through the routed Hermes model;
- preserve truthful model footer metadata;
- apply cooldown, interruption, and fixed quiet-hour safeguards;
- record Circadian, Sleep/Quiet, and Proactive Quality decisions in shadow mode;
- use confirmed fine-grained location only as optional weather context;
- persist replaceable source separately from user/runtime state.

Current Circadian and quality enforcement is available only behind the isolated
acceptance guard:

```text
HERMES_ALIVE_DELIVERY_ENFORCEMENT_MODE=isolated
HERMES_ALIVE_RUNTIME_SCOPE=isolated_test
```

Both values are required. They are intentionally unavailable through managed
production configuration.

## Hard safety boundaries

- Control and system-critical messages are evaluated before social sleep gates.
- System errors, security/service alerts, explicit reminders, Email Watchdog,
  control commands, and business-critical notices remain hard-exempt.
- User silence may produce at most one mild probabilistic affective pulse per
  silence episode; it must not become repetitive escalation.
- Task-state wording requires fresh structured evidence.
- Weather wording must not claim a robot location or bodily sensation.
- Provider secrets stay with Hermes.
- Production gateway restart, production source/config changes, and real
  message delivery require explicit approval.

## Lifecycle

```bash
scripts/hermes-alive-lifecycle install
scripts/hermes-alive-lifecycle configure
scripts/hermes-alive-lifecycle verify
scripts/hermes-alive-lifecycle status
scripts/hermes-alive-lifecycle uninstall
scripts/hermes-alive-lifecycle purge
```

- `install` and upgrades are transactional and restore the previous source/hook
  when validation fails.
- `uninstall` removes source, active hook, and managed configuration while
  preserving learning/runtime state.
- `purge` removes all Hermes Alive-owned shared state and is destructive.

## Source layout

```text
skills/hermes-alive/
├── SKILL.md
├── LICENSE
├── hooks/
├── scripts/
├── templates/
├── tests/
└── docs/
```

The active hook is installed at `/opt/data/hooks/hermes-alive`. Persistent state
lives under `/opt/data/hermes_alive_shared` by default and must not be stored in
the source directory.

## Validation

```bash
cd /opt/data/skills/hermes/hermes-alive
bash tests/run_all.sh
```

Final production consideration additionally requires a fresh-container install
from the real GitHub repository, Provider/personalization onboarding, full
matrix and default-scale stress tests, lifecycle and persistence checks, an
approved spare-WeChat end-to-end test, and clean uninstall/purge verification.

## Documentation

- `docs/ARCHITECTURE.md`
- `docs/RUNTIME_POLICIES.md`
- `docs/LIFECYCLE_AND_PERSISTENCE.md`
- `docs/DATA_AND_PRIVACY.md`
- `docs/TESTING_AND_ACCEPTANCE.md`
- `docs/DISCOVERY_DEVELOPMENT.md`
- `tests/TESTING.md`

## Implementation constraints

- Hook modules are loaded flat; use absolute imports between hook files.
- Required hook events are `gateway:startup`, `session:start`, and `agent:end`.
- Runtime state paths must honor `HERMES_ALIVE_SHARED_DIR`.
- Proactive model-authored messages use `is_system=false` and carry the resolved
  model through all footer metadata fields.
- Startup-ready notifications belong to `hermes-wechat-enhance`, not Hermes
  Alive.
- Optional Playwright discovery is outside the core lifecycle contract and must
  use a persistent browser path when enabled in containers.
