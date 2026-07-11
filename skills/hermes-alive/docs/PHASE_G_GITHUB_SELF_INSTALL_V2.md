# Phase G GitHub self-install V2

Marker: `HERMES_ALIVE_GITHUB_SELF_INSTALL_V1`

Final distribution is a complete GitHub repository. A fresh-container
acceptance run receives only the GitHub URL or official GitHub skill
identifier. The harness must not copy files into `/opt/data/skills` or
`/opt/data/hooks`.

Preflight may emulate GitHub with an isolated local Git origin. Final Phase I
must clone/install from the real GitHub repository.

Provider readiness is determined from the configured Hermes model, not from
the exit code of `hermes config check`.

Installation does not recursively chmod persisted runtime or learning state.
