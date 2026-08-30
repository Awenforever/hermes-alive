# Hermes Alive

Hermes Alive is a gateway-native proactive companion for Hermes and WeChat. The
repository contains the complete skill source, lifecycle tooling, tests,
documentation, repository metadata, and portable CI.

- English skill documentation: [`skills/hermes-alive/README.md`](skills/hermes-alive/README.md)
- 中文说明：[`skills/hermes-alive/README_CN.md`](skills/hermes-alive/README_CN.md)
- Architecture: [`skills/hermes-alive/docs/ARCHITECTURE.md`](skills/hermes-alive/docs/ARCHITECTURE.md)
- Testing and acceptance: [`skills/hermes-alive/docs/TESTING_AND_ACCEPTANCE.md`](skills/hermes-alive/docs/TESTING_AND_ACCEPTANCE.md)

## Repository layout

```text
skills/hermes-alive/       complete installable skill
scripts/bootstrap.sh       repository-level install/configure/verify entrypoint
scripts/portable-ci.sh     public CI and repository integrity checks
scripts/verify-repository.py
metadata/                  version, source manifest, and release-stage facts
.github/workflows/ci.yml   portable GitHub Actions workflow
```

## Safe installation

Clone the complete repository, then run:

```bash
bash scripts/bootstrap.sh
```

The bootstrap delegates to the skill lifecycle. It does not modify Hermes Core
or `weixin.py`, does not restart production, and does not send a real WeChat
message.

The default configuration:

- enables the live proactive quality governor;
- enables production Circadian `live` enforcement;
- enables dynamic Sleep/Quiet live enforcement at the watcher pre-compose boundary;
- keeps the isolated dual-key delivery-enforcement helper test-only;
- leaves weather disabled until location is explicitly confirmed;
- stores shared state under `$HERMES_HOME/hermes_alive_shared`.

## Verification

```bash
bash scripts/portable-ci.sh
```

Portable CI verifies repository structure, manifests, documentation links,
compilation, and the suites that can run with a deterministic test double. Full
Hermes-runtime attribution and complete lifecycle acceptance remain separate
isolated release gates.

## Release status

This repository is the **v2.4.3-rc.1 candidate**, not a final production
deployment. The Circadian + Dynamic Sleep/Quiet production-enforcement patch
has passed exact-base isolated acceptance in the current production image,
including full regression, default-scale stress, persistence across container
recreation, uninstall/reinstall, and purge/reinstall checks.

The remaining release path is deliberately separate:

1. verify this repository candidate and Git bundle transport;
2. publish the guarded `v2.4.3-rc.1` ref only after explicit approval;
3. install from the real GitHub URL in a fresh isolated container;
4. run spare-WeChat end-to-end acceptance with explicit approval;
5. perform controlled production upgrade, rollback validation, and
   post-restart persistence/real-path acceptance.

The currently running production remains the previously accepted v2.4.2
release until that upgrade path is completed.

## License

[MIT](LICENSE)
