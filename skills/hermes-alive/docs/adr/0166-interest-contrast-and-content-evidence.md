# ADR0166 — Measure interest effects and preserve discovery meaning

Date: 2026-10-18. Status: implementation and prospective verification in progress.

## Evidence and scope

Production remains unchanged. The previous tree a02cc33 (commit 2ba3352) passed
portable CI with 60 retained logs; this is not personalized usefulness acceptance.
The new opt-in native probe uses one synthetic owner and the same four operator-
collected public reference pages throughout five phases: no profile, interest A,
explicit replacement with B, reopen B, and withdrawal B. It has no delivery route,
selection, send authorization, or action attempt. It records actual native model
completion evidence and first error, never an automatic satisfaction score.

Real r1 completes five calls, all actual qwen3.8-reasoner/custom:ustc, with retained
interpretations recovered without inference, pending workers0 and action/dispatch0.
Baseline abstains; interest A also abstains, despite recognizing the relevant
resource, because the model conflates a withheld sending grant with a prohibition
on internal proposals. Corrected B and reopened B each propose the relevant
reference despite the same no-grant qualification. Withdrawal returns to abstention.
Thus profile reaches inference and corrections survive reopening, but behavior is
inconsistent: this is NOT five clean rounds, a causal learning proof, an extraction
test over noisy conversation, or a complete autonomous-chain test.

Public evidence was checked at https://www.ifixit.com/Device/Bicycle,
https://www.rhs.org.uk/container-gardening,
https://science.nasa.gov/skywatching/ and
https://www.metmuseum.org/art/collection. Descriptions identify general references,
not new events, firsthand assistant observations, or recipient-specific advice.
No actual owner's interests or accounts belong in distributed fixtures/defaults.

## Decision

Clarify the internal stage contract in the model input as well as the system
instructions: it does not route, send or authorize execution. Recipient relevance
and execution eligibility are distinct questions. No grant must not fabricate a
negative interest; a preference must not become a grant. Explicit boundaries on
content, contact, or proposing/discussing remain binding. Existing candidate
authority and later authorization checks are unchanged. Do not patch particular
user phrases or force a nonempty candidate list to make this experiment pass.
Run r2 prospectively with the same materials/preferences and new history; retain
r1 and its failure regardless of r2 results.

R2 outcome: two actual Qwen3.8/custom:ustc calls, baseline abstention recovered
without inference, then a relevant A candidate with three correctly excluded
topics. However its response omits the final outer JSON brace. The actual failed
receipt records ModelJSONError; the probe stops at that phase. No B/reopen/
withdrawal phase is run in r2. Preserve this failure; neither automatically append
a brace nor classify the raw candidate as an admitted result. Pending workers0,
action attempts0, authorization evaluations0, external dispatches0, sends0.
Both real containers are terminal and their exact model projections removed.
This is evidence motivating explicit bounded model-mediated format recovery,
not permission for blind retries, deterministic authored content, or a clean
semantic/production acceptance claim. The proposed stage distinction has only
partial prospective evidence so far.

Discovery evidence also needs substance before semantic selection. Bilibili's
existing popular collector retained mostly view/danmaku counts and discarded the
publisher's description/date. Preserve the description (bounded with an explicit
truncation marker), creator and publication time. Distinguish publisher-supplied
description from video-body access; when absent, explicitly retain the listing-
only evidence limitation. These are source observations, not generated summaries
or claims the assistant watched the video. Tests trace the description to the
actual opportunity model input through legacy admission and the protected vault.

## Unresolved product work

The collector still retrieves general popular videos, not personalized searches.
The discovery reader selects a bounded window by agenda order (collector priority
included) before seeing interests. Material outside that window cannot be recovered
by a better final prompt. Profile-aware discovery and candidate recall remain open;
increasing a numerical limit or adding topic keyword gates alone is not a solution.
Noisy-conversation extraction, source diversity/accessibility and longitudinal
recipient value still need their own actual tests. This ADR does not declare them
solved or authorize deployment.

Offline testing: initial new stage-contract assertion incorrectly assumed every
existing test invocation had authority=none; a delegated fixture exposed the test
mistake. Both authority paths retain their original behavior after correcting the
assertion. Recovery/consent boundaries were not loosened to satisfy the test.
Final isolated seven-entry regression passes opportunity/context synthesis,
video evidence admission to the model input, source support/history, composed
expression and commitment cognition. Separate editorial/discovery-pivot tests
pass, but their local runtime logs an unavailable PyYAML import and falls back
to default source config: that run does not qualify configured production fetch.
No full portable rerun has been performed for this changed tree yet.
