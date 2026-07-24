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
- keeps Circadian in `shadow`;
- keeps dynamic Sleep/Quiet integration `observe_only`;
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

This repository is a **candidate**, not a final production release. The current
source and lifecycle have passed isolated acceptance, but the remaining path
still includes:

1. bare-repository and Git bundle transport verification;
2. installation from a real GitHub URL in a fresh container;
3. spare-WeChat end-to-end testing with explicit approval;
4. controlled production deployment and rollback;
5. restart/persistence checks and stability observation.

Circadian and dynamic Sleep/Quiet shadow components are not counted as
production-enforced features.

## License

[MIT](LICENSE)
