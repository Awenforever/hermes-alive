# ADR-0288 — Preserve proactive contact hours at cutover

Status: migration evidence verified in isolation. Native timing policy remains open.

## Evidence

An isolated upgrade from official Hermes 0.21.3 with released Alive 2.9.8 to
Hermes 0.22.5 with Alive candidate `c2f7bb2` retained a readable session,
an approved synthetic pairing and byte-identical environment, user memory,
legacy Alive settings and legacy state. Restoring the pre-upgrade snapshot
in a separate profile reproduced the same witness under the old versions.
The candidate stayed inactive. This qualifies that fixture's data custody and
snapshot rollback. Channel authentication, actual outbound behavior, external
memory and the live production procedure remain separate gates.

The restored legacy evaluator applies the fixture's `22:45–08:15` interval
in `Asia/Shanghai`, including the correct start, midnight and end boundaries.
The installed candidate's `alive setup --help` exposes no contact-hours
choice. In the Native path, `kernel_execution_bridge.enable` sets a static
`can_interrupt=True`. The host's dispatch eligibility checks delegation cadence,
and the standard adapter path revalidates authority but has no time-of-day
check. The saved setting therefore has no behavioral effect after Native
activation. A matching file hash does not qualify this migration behavior.

## Cutover requirement

Treat contact hours as a preference about when to interrupt the owner. Keep
it independent from recipient identity, consent to retain a share, and scope
for background work. During setup show the effective legacy fixed interval and
time zone when present. Let the owner keep it, replace it or choose unrestricted
contact. Preview conflicts or invalid settings and require an explicit choice
before Native cutover. Preserve legacy files for rollback. Learned Circadian
history needs its own migration decision and evidence, especially where the
effective legacy timing is dynamic.

The Native policy must prevent new proactive dispatch during quiet hours and
be checked again at the actual adapter handoff after any lengthy generation
or proof reconstruction. Defer through the existing host lifecycle with an
auditable reason. The next eligible wake re-evaluates context and freshness;
it does not reuse an expired permit or replay the stale draft automatically.
Independent background tasks, user-initiated conversation and Core's own
messages follow their existing authorization. If an adapter has already
accepted a message, the adapter owns its lifetime; Alive creates no second
queue and makes no claim about the later delivery time.

## Required qualification

- Old profile with a non-default interval, new profile with a chosen interval,
  and existing Native profile reconfiguration. Cover unrestricted mode and
  invalid/conflicting legacy settings.
- Real installed Core with the same owner binding across restart. Exercise
  daytime and overnight intervals, local time boundaries, daylight-saving
  transitions, and the Windows time-zone data source.
- Cross the quiet boundary during preparation and immediately before adapter
  handoff. Verify zero new adapter submissions, intact unrelated work, and
  fresh deliberation after quiet hours. Prove there is no stranded dispatch
  or false submitted/delivered record.
- Repeat the legacy profile cutover with observable transport in a test
  environment before claiming that quiet-hour behavior migrates.
