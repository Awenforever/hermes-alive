# Phase G Lifecycle Productization V1

Markers:

- `HERMES_ALIVE_LIFECYCLE_V1`
- `HERMES_ALIVE_ATOMIC_INSTALL_V1`
- `HERMES_ALIVE_MANAGED_CONFIG_V1`
- `HERMES_ALIVE_CLEAN_UNINSTALL_V1`
- `HERMES_ALIVE_MANAGED_CONFIG_LOADER_V1`

This phase turns the A–F behavior candidate into a lifecycle-managed skill.

The official Hermes transport contract is:

- direct `SKILL.md` URL: single-file only;
- GitHub/tap identifier: complete skill directory;
- official uninstall: removes the hub-installed source directory.

Hermes Alive owns activation of `/opt/data/hooks/hermes-alive`, its managed
non-secret configuration file, install manifest, rollback, verification, and
state-preserving or purge uninstall.

Provider secrets remain owned by Hermes. The lifecycle CLI detects readiness
through `hermes config check` and guides the user to `hermes setup model`.
