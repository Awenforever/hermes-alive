# ADR0211 — Guided setup binds choices to an authorized Core conversation

Date: 2026-10-24 (Asia/Shanghai), Codex.
Status: configuration/continuity prerequisite implemented; live activation and
ordinary consumer/migration qualification remain pending.

## Problem

The only prior kernel CLI configures non-sending shadow work with a raw user ID.
It cannot establish the scoped receiving conversation or an ordinary authorized
delivery runtime. Manually wiring test objects is not an installation contract.
Old user-ID subjects cannot safely become scoped v2 owners by inference.

## Configuration flow

1. The operator's Core plugin CLI stages separately approved model calls,
   delivery, outbound conversation retention and optional public search choices.
   A model alias defaults to Core inheritance; no keys or provider configuration
   are copied into plugin settings. Model or delivery approval does not imply
   permission to save history or search private interests.
2. A private pending document and signed structural intent issue a 15-minute,
   one-use confirmation. Config holds only an intent ID. Show the choices before
   asking the user to send the command in the intended authorized conversation.
3. A Core-registered async command uses Core's actual admitted source/session
   dispatch, canonical current receiver and exact persisted route. No task-env
   guess, recent conversation, alternate bot or synthetic routing session.
4. The signed confirmation seals the actual private scope and chosen options,
   derives scoped v2 ownership and applies only the explicit outbound retention
   choice. It attaches the real main-turn reader. No policy is enabled, no route
   delegation minted, and no model or transport is called. The installation is
   configured_not_activated, never mislabeled operational.

The protected configuration lives until removed as disclosed; conversation
history has its separately chosen retention. The pending unowned topic duplicate
is erased after successful confirmation. Replacement is explicit and preserves
history. A used code cannot switch owner/thread; a stale or superseded code is
not reusable, including after protected content erasure. Core still owns
pairing/admission; matching JSON alone never proves it.

## Recovery and migration boundaries

- The private store/journal are authority; Core settings are inventory hints.
  Concurrent setup is checked under the journal writer lock. No models/messages
  occur while confirmation is incomplete or superseded.
  Setup signatures cover the complete event envelope as well as payload: actor,
  identity, causation and the 15-minute deadline cannot be changed independently.
- Recovery of a missing retention write is fenced by the original confirmation
  sequence. A later OFF remains OFF, even when projection receives earlier facts
  out of order. Ordinary repeat confirmation cannot renew retention or permission.
- Initialization of an empty store is an explicit operator action. Status and
  startup cannot seed missing identity/content keys; partial migration refuses.
  A nonempty unrecognized directory is not an empty installation. A surviving
  Core setup hint also prevents reseeding a completely missing store.
  An existing truncated identity key is invalid, never accepted or padded.
- Preserve the existing installation key, old raw-user subjects, encrypted
  content, grants and runtime state. Do not rename/merge/delete these as migration.
  A supported, explicitly reviewed legacy transition still has to be implemented.
- Local enable refuses this not-yet-activated kernel rather than starting legacy
  as a fallback. Full live assembly/supervision, stop/resume/expiry and user-guided
  source customization remain part of the actual objective, not future niceties.

## Qualification

Test the installed candidate bytes through public Core discovery, actual Core CLI
and native Gateway plugin-command dispatch. Synthetic peers and no-network
execution prove only that boundary, not real pairing/transport or consumer
dependency admission. Exercise no session, wrong user/thread, replay, superseding
intent, restore after missing first write, later OFF, out-of-order projection,
erased configuration, missing keys, legacy-state preservation and runtime
uninstall/reinstall. Inspect structured refusal reasons, not only exit codes.
The full consumer/fleet lifecycle, real daemon restart, memory/legacy migration,
natural older-share follow-up and ten full-chain quality rounds remain open.
