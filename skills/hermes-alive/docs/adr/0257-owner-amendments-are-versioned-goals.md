# ADR 0257 — Explicit owner amendments are versioned goals

Status: implemented candidate; actual Core qualification in progress.
Date: 2026-10-27.

## Product behavior

A user can amend an ongoing task, its constraints or its deadline through the
existing Core main-turn tool. The main model interprets the current request; the
plugin verifies owner, exact current turn/evidence, separately guided revision
consent and latest item version. Omitted fields stay unchanged. An explicit null
deadline removes it. A correction is not permission to expand automatic toolsets.
Old installations do not acquire this capability from the older management flag.

Keep the same item identity, the original request and chronological amendment
sources. The current effective description remains an interpretation, never a
verbatim quote. Retained original plus amendments have a complete bounded 6000
character view; unavailable/oversized history cannot silently authorize Native
work. A revision does not silently extend attention or data retention. Conflicting
deadlines require clarification rather than a guessed schedule/retention change.

## One fact, existing projections

The protected current-owner intake receipt is itself a typed `agenda.revised`
fact. Its signed binding contains the exact previous version/transition and the
new private content reference/deadline. It is not a model-authored claim of user
confirmation. The same existing agenda projection applies it in journal order
and rebuilds it after a crash. Do not persist a receipt and separate mutation
intent that can diverge between two commits. Vault bodies are written before the
fact; an orphaned encrypted body is not an admitted task or an action grant.

Existing Core work guards consult admitted amendment metadata even before its
projection. Old-version tools are fenced, including manually submitted producer
jobs and already admitted inspectors. This is not process cancellation, rollback
or replacement execution. Surface that distinction in work status. Attention-only
snooze/resume retains ADR0256 behavior; a goal/deadline revision is a new execution
version. Outcome assessment cannot close the new goal from the old job's success.

## Scope and qualification

No second executor, scheduler, channel, physical queue or independent inference
router. Core still owns actual jobs/models/permissions. The candidate is not a
general continuation planner or dependency implementation. Actual main-model
interpretation, real followup after a revision, in-flight/unload and coordinated
source-dependent erasure/migration remain explicit gates. Do not infer them from
synthetic tool replies, type/schema checks or the preceding full CI baseline.
