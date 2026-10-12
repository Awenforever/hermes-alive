# Public baseline upgrade and dormant rollback — 2026-10-12

## Provenance and scope

GitHub `refs/heads/main` was read directly and matched local
`aaf6126fccb767e42096832e5ed2e8712010f44f` (Alive 2.9.8). Its exact Git tree,
without local worktree changes, was archived as the baseline. The target is
the new-kernel development branch. It still carries 2.9.8; this is a source
revision upgrade, not a claimed published semantic-version upgrade.

The opt-in admission runner now accepts `--baseline-package <complete tree>`.
Both trees are cloned as independent disposable Git fixtures and installed via
the public Hermes package CLI on official source snapshot
`f925b01791fe052e7d55dc975750c0bd985aff91`. This is not newest-upstream or real
GitHub transport qualification. The NAS/Linux test container retained scanning,
Hermes dependency management and the one-CPU/2-GiB/256-PID resource boundary.
No production mount, real authorization, gateway launch or live message was used.

## Observed pass

1. Public baseline package and runtime installed; `alive status` loaded in the
   intended disposable profile and proactive delivery remained disabled.
2. Seeded existing-user fixture files included managed preferences, a legacy
   state record, voice/source markers, an empty context queue and a synthetic
   `.env` authorization marker. Installed the new package and runtime.
3. Every seeded file remained byte-identical. Status remained non-proactive.
   The installed new kernel source matched the intended target, not the old
   tree or an incidental test-runner import.
4. The Hermes-selected interpreter created real synthetic journal/checkpoint,
   identity key and encrypted-content state. Repeated runtime install retained it.
5. Reinstalled the baseline package and runtime. Baseline source was restored
   exactly and the installed skill's hook source tree did not retain new kernel code.
   Legacy configuration/state remained byte-identical and status remained off.
6. Reinstalled the target package/runtime. The original journal event,
   checkpoint, identity/content keys and decryptable content all passed again.
7. Same-revision refresh, runtime uninstall, package removal and complete
   package/runtime reinstall also preserved the fixture files and encrypted state.
   The process exited zero.

Observed completion markers:

```text
HERMES_ALIVE_BASELINE_REVISION_UPGRADE_OK
HERMES_ALIVE_DORMANT_ROLLBACK_REUPGRADE_OK
HERMES_ALIVE_INSTALL_ADMISSION_OK
```

Local admission contract regression also rejects an incomplete baseline before
any subprocess installation command. Default invocation remains opt-in/skipped;
it never uses an existing production profile as its test target.

## Limits: preservation is not complete behavioral migration

The legacy state/voice/source files contain synthetic preservation markers,
not a qualification-sized corpus of every historical schema. Only proactive
enablement was interpreted through status; retained timezone/quiet preferences
were not tested against a running scheduler. The `.env` marker is not a working
credential: retaining bytes does not prove an external authorization still works.

Rollback was dormant. Old code need not interpret the new kernel; it must leave
that state intact for re-upgrade. This test does not prove in-flight/live/crash
rollback, backwards interpretation of new learned state, model/channel swaps,
authorization migration or Windows/WSL portability. Those gates remain open.

A read-only production metadata check found the legacy proactive log present
and no new-kernel journal. No content was printed or imported. Production still
runs the legacy implementation; do not describe these isolated passes as live
kernel learning, shadow decision parity or production acceptance.
