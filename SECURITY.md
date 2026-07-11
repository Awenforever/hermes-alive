# Security Policy

## Supported version

Security fixes are applied to the current `main` branch and the latest
published release.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability or credential leak.
Use GitHub's private vulnerability reporting feature for this repository.
Include the affected version, reproduction steps, impact, and any proposed
mitigation.

Hermes Alive must never require users to place Provider credentials, platform
tokens, or private chat identifiers in this repository. Those values belong
in the local Hermes configuration and managed runtime state.
