# Changelog

All notable public repository changes are documented here.

## Unreleased

## v2.4.1 — 2026-07-14

### Added

- Focused Discovery Quality and rich-content model-attribution regression suites.

### Changed

- Discovery and rich-content delivery now preserve structured Provider model attribution through content references, Weixin rich payloads, and footers.
- Rich-only and hybrid text-plus-rich delivery count as one logical sent event and one cooldown commit.

### Fixed

- Stale or unsupported proactive continuation of old debugging and task topics is blocked.
- Rich-only delivery now records logical sent state without counting multiple transport bubbles as multiple proactive messages.
- Real Provider model identity is retained for normal, fallback, link, image, and file delivery paths.


### Added

- Circadian shadow state, sleep/quiet comparison, proactive quality governance, fine-grained location onboarding, joint replay, and dual-key isolated enforcement.
- Complete GitHub repository bootstrap and lifecycle management.
- Managed non-secret personalization configuration.
- Matrix and full-scale stress suites with fake Provider and platform adapters.
- Transactional install rollback, clean default uninstall, and purge.
- Public repository security, contribution, license, and CI metadata.

### Changed

- Replaced the terminal-style personalization questionnaire with zero-touch
  configuration: timezone is auto-detected, quiet hours use safe defaults, and
  Hermes asks at most one optional weather-location question in the existing
  chat.
- Restored the polished bilingual public README and consolidated historical phase notes, duplicate skill READMEs, obsolete policy generations, and internal references into a small canonical documentation set.
- Public documentation now uses the GitHub repository and lifecycle contract.
- CI declares least-privilege permissions, job timeouts, and a fixed PyYAML
  version.

### Fixed

- Publication formatting issues in the skill README and `alive_state.py`.
- Weixin proactive delivery now resolves the configured bot/home target to the
  canonical inbound peer when context-token and session evidence are
  unambiguous.
- System proactive tests now check `SendResult.success`; failed sends remain
  queued instead of being logged as delivered.
