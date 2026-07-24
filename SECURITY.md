# Security Policy

## Supported branch

Security fixes are prepared against the `main` branch of this repository
candidate. No production deployment is implied by a source change.

## Reporting

Do not place credentials, private chat content, WeChat session material, Provider
tokens, cookies, or production configuration in a public issue.

A security report should include:

- affected commit or tag;
- reproducible steps using synthetic data;
- expected and actual behavior;
- whether the issue affects source, lifecycle, delivery, or persistence.

## Boundaries

Hermes Alive must not:

- modify Hermes Core or `weixin.py`;
- store Provider credentials;
- expose raw private URLs/titles in topic history;
- send a real message during CI or installation;
- restart or modify production without explicit approval.

The repository CI uses deterministic fakes and disabled Provider/WeChat delivery.
