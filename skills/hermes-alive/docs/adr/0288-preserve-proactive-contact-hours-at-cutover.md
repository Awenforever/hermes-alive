# ADR-0288 — Preserve proactive contact hours at cutover

Status: migration evidence verified in isolation. Native fixed-hour candidate under qualification.

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

## Candidate behavior

The setup CLI previews legacy timing and records the chosen fixed interval or
explicit unrestricted choice in the confirmed owner configuration. A previously
confirmed interval survives replacement setup unless the owner changes it.
An older Native configuration without an explicit choice cannot enable proactive
contact when legacy timing is present. An already active older configuration in
that state withholds proactive submissions until the owner reconfigures it.

The runtime checks contact timing before preparing a proactive candidate, after
draft preparation and before entering the real adapter. It closes the cycle
with `contact_hours_closed` and leaves the existing timer responsible for the
next wake. A cutoff after the durable dispatch start leaves that permit consumed
and records an authenticated local hold. The hold keeps that draft out of
ordinary conversation continuity and is neither an adapter observation nor a
delivery receipt. It can conservatively consume the original cadence reservation.
The separate dynamic Circadian policy is previewed as requiring an explicit
choice, with its state preserved for legacy rollback.

## Isolated qualification

On exact candidate `456633b`, actual Core 0.22.5 setup displayed the previous
fixed window, required an explicit choice and persisted the owner-confirmed
window without changing the legacy file. An offline two-process test then
enabled Native in the confirmed conversation. Core's startup hook reopened
the same session, configuration and activation from disk after the first
process exited. With a controlled civil clock and an admitted synthetic public
source, both processes recorded `contact_hours_closed` at 08:14. Work-state
reconciliation ran and neither process attempted a model or adapter call while
quiet. At 08:15 the supervisor reached one fresh synthesis with a controlled
completion and chose silence, with zero adapter submissions throughout.

The separate real-Core continuity and standard-channel tests covered a cutoff
after share preparation and immediately before handoff. They confirmed no
adapter observation, no replay of the consumed start and no held draft in the
ordinary follow-up context. Windows passed the controlled schedule and
standard-channel suites. Actual platform daemon restart, real-channel behavior,
active background job progression across a cutoff and dynamic-policy migration
remain open.
