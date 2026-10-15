# ADR 0145 — Model-reasoned revisit timing, not scheduled delivery

Date: 2026-10-15. Status: isolated implementation and one actual-model story;
not production activation or general longitudinal qualification.

## Decision

ADR 0144 supplies a bounded host wait but not a semantic timing judgment. Extend
opportunity interpretation with optional `reconsiderations`: an original abstained
agenda ID, integer `after_seconds` in 1–86400 and a brief reason. The model reasons
from actual context, not a keyword classifier. A suggestion is internal cognitive
work, not a user deadline, permanent preference, commitment, send timer or authority.

Only an accepted source-linked abstention can support a hint. Positive, foreign,
unassessed and duplicate source hints are rejected, without throwing away separately
valid proposals or non-action. Invalid optional envelopes are counted as rejected
advisories, not repaired by guessing fields. Canonical retained accepted hints have
bounded rejection counts on reopen; the full rejected raw response is not claimed
to be retained by the interpretation store. Model diagnostic reports keep raw output.

Interpretation now retains its exact prompt `as_of` as structural metadata. Relative
suggestions resolve against that original instant; reopening never recalculates
them from today's clock. Reasons stay in the encrypted candidate bundle under its
existing source/feedback retention bounds. The result exposes typed source-linked
reconsideration objects; it does not create user memory or send an action.

The existing wait ledger associates original agenda/observation/interpretation
references with their review instants, including a grounded correction's retained
interpretation if applicable. Its deadline is the **earliest** of host window,
source/agenda boundaries and model suggestions. Already-due suggestions cannot
restart their countdown. New input, source changes, erasure and current policy
continue to wake/revoke wait before that instant. Every actual send still requires
its separate current selection, wording, authorization and outbox checks.

This connects source-linked internal reconsideration to existing persistent
opportunities and the host. It does **not** mutate a user commitment into a timer,
create a second discovery item per tick, or claim the general commitment planner
is complete. Rich user work/commitments and reflective agenda evolution remain open.

Wait method v2 binds timing lineage. Authenticated v1 events remain readable as
history but are not used as v2 waits. Unknown or forged methods/aliases fail
explicitly; no historical payload or incrementally produced user data is replaced.

## Tests and failures preserved

`run_semantic_reconsideration.py` passes Windows and network-disabled/read-only/
resource-limited Linux. It checks fixed prompt anchoring, exact reopen, no-spend
waiting across restart, new inbound reopening before deadline, source and reasoning
privacy, v1 historical rejection as a current wait, invalid/duplicate/foreign/positive
source suggestions, malformed optional envelope isolation, mixed valid candidates
and hints, and no action/preference/dispatch records. Existing opportunity abstention,
bounded wait, host identity, route-preflight and review-recovery regressions pass
Linux; the original abstention fixture also passes Windows.

The first new fixture failed because the old candidate-envelope parser did not
allow the new optional top-level key. A synthetic-only trace located that actual
runtime integration error, which was fixed before inference. An initial trace
wrapper itself lacked the test import path; it is not a runtime failure or pass.
These tests use retained-module overlays, not fresh installed-device qualification.

## Actual model observation

`probe_alive_live_temporal_reconsideration.py` provides a bounded opt-in diagnostic
with empty private output, raw prompt/results, model routes, counts and no channel.
The canonical environment, source and user statements are synthetic fixtures.

The terminal run `model-only-temporal-20261015-r1/results/report.json` made six
logical / six observed HTTP starts:

- An explicit temporary 45-minute meeting yielded abstention plus a 2700-second
  revisit suggestion; no share was generated, and no autonomous memory was written.
- Reopening on the unchanged context after a runtime restart yielded
  `waiting_for_change`, same deadline and **zero** provider callback attempts.
- A new explicit statement that the meeting ended early superseded the old
  time-bounded availability fact. A fresh shadow cycle generated, source-reviewed,
  selected and expressed a relevant guide, preserving unverified availability.
  It did not wait out the old 45-minute suggestion and made no action attempt.

The reason's conversational phrasing about a later share is a model interpretation,
not permission; code stores a review instant only. This is a single story, with
same-family source/fidelity reviewers, not independent semantic truth, user utility,
final authorization or real delivery. Probe `finished`/exit-zero do not certify
semantics; the raw outputs and each stage were inspected separately.

Credential export was removed after the terminal container; production start time
was unchanged during the job. No production configuration, private history,
Enhance/Core, model/fallback, proxy or other-plugin change/restart/deploy occurred.
Cumulative actual totals: **173 logical / 186 observed HTTP starts**, actual sends zero.

## Continue the original objective

Qualify uncertain duration, overdue/contradictory context, multiple independent
agenda items and long-running usefulness rather than treating one clock match as
completion. Connect commitments and genuinely attributed reflection/learning,
derive effective host/model configuration identity on install/upgrade, complete
privacy/physical forgetting and lifecycle ownership, then portable migration/
rollback and real production ten-clean acceptance. No production enablement follows
from this ADR alone.
