# Changelog

All notable public repository changes are documented here.

## Unreleased

### Added

- Circadian shadow state, sleep/quiet comparison, proactive quality governance, fine-grained location onboarding, joint replay, and dual-key isolated enforcement.
- Complete GitHub repository bootstrap and lifecycle management.
- Managed non-secret personalization configuration.
- Matrix and full-scale stress suites with fake Provider and platform adapters.
- Transactional install rollback, clean default uninstall, and purge.
- Public repository security, contribution, license, and CI metadata.

### Changed

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
