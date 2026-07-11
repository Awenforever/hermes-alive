# Hermes Alive public repository contract V1

Marker: `HERMES_ALIVE_PUBLIC_DOCUMENTATION_CONTRACT_V1`

## Distribution

The distribution unit is the complete GitHub repository
`Awenforever/hermes-alive`. A standalone `SKILL.md` is not a complete
distribution.

## Installation

Supported public paths:

1. clone the repository and run its root `bootstrap.sh`;
2. use Hermes GitHub skill transport, then run the installed lifecycle CLI.

The installer owns final source/hook placement. Test harnesses must not pre-copy
files into final skill or hook directories.

## Configuration ownership

- Provider credentials and model configuration belong to Hermes.
- Hermes Alive managed configuration contains only non-secret personalization.
- Explicit process environment variables override managed values.
- Production restart and real-message delivery require explicit approval.

## Lifecycle

- install/update is transactional and restores the previous source/hook on
  failure;
- default uninstall preserves learning/runtime state;
- purge removes all Hermes Alive-owned state;
- verification checks compilation, manifest and source/active-hook parity.

## Acceptance

Before production consideration:

- fresh Git clone plus bootstrap;
- Provider guidance and personalization;
- matrix and full-scale stress suites;
- container recreation persistence;
- default uninstall, reinstall and purge zero residue;
- spare-Weixin real e2e in a disposable container.
