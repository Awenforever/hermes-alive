# ADR 0082 — Recover learning control from owner events, not state caches

Status: implemented; focused local regression passed. Real gateway feedback
authentication, interpretation quality and long-term user benefit are unproved.

## Actual baseline evidence

The same new regression tests were copied into an isolated archive of commit
`188ab23`. Reflection approval by `user:other` was accepted (`user_accept`), and
that actor's preference withdrawal was accepted (`user_retracted`). This extends
ADR 0081's ownership defect to control operations, not just outcome attribution.

State caches were also authority-bearing: reflection reads trusted their accepted
flag, preference reads trusted their active flag, and learned reflection sources
trusted a cached transition. A restored or delayed projection could consequently
misrepresent user control even when the original journal retained the true events.

## Design

`owner_review_source` centralizes the personal principal and chronological causal
boundary for reflection reviews and preference withdrawals. It requires canonical
target/input/operation ordering and same-owner scope. It is explicitly not gateway
authentication: a host that can forge the owner's actor string is not qualified.

`ReflectionProjection.verified_state` validates the original proposal and its
exact evidence basis, then folds valid owner reviews in journal sequence order.
It returns the authoritative state and latest valid review event. Invalid foreign
reviews, duplicate transitions, and approval after expiry do not change state.
Current reads include a pending valid withdrawal before projector acknowledgement;
approval/withdrawal application uses the fold before its own event. Cached state
and transition rows remain recovery conveniences, never approval evidence.

Preference estimates similarly check canonical owner withdrawal events rather
than an active/retracted cache flag. Accepted-reflection signals must reference
the exact valid approval event and remain within the original reflection's current
expiry, even if the derived signal has a longer retention horizon. Recovered
reflection timestamps come from the canonical controlling event, not cached time.

The proposal evidence check preserves the existing distinction: explicit feedback
or repeated operational task evidence can support a reviewable hypothesis; delivery
success alone cannot establish benefit. Evidence must precede its proposal in both
journal and observed time, remain owner-scoped and not exceed the proposal's privacy
classification. This neither approves a hypothesis nor authorizes an external act.

## Local functional checks

- Foreign human and model principals cannot accept/reject a personal reflection
  or retract its preference signal; genuine owner positive controls still pass.
- A forged accepted cache cannot approve an unreviewed proposal. A stale proposed
  cache cannot undo an actual approval or prevent its valid subsequent withdrawal.
- Pending canonical withdrawals suppress current advice immediately. Restoring
  accepted/active flags cannot resurrect it. Journal and original private content
  are not deleted by withdrawal.
- Learned reflection evidence expires after its original 90-day basis, even when
  the derived observation is retained 180 days; 70-day positive control still applies.
- CognitionLearningReader and opportunity synthesis still invalidate an old model
  interpretation after withdrawal, including a stale restored active flag.
- Python 3.14 reflection, preference learning, learning context, outcome and
  evaluation suites pass. Source/meaning/authentication and utility qualification
  are separate from these synthetic control and recovery checks.

## Boundaries and next work

The same five suites pass on NAS managed Python 3.13, network-none and with the
owned scratch tree mounted read-only. Input tree
`fe474b12bf0cd8cffbb292f6bca2758fdfb6ac77`, archive SHA256
`26e01b31b99066e2f0ec2d67f689ee58acd9d1f391a7e3d6fbb5d2bc5b18f9a4`.
Container `alive-owner-control-offline-20261013-r1` exited 0, start
`2026-10-13T15:20:22.730553756Z`, finish `2026-10-13T15:20:27.915735547Z`.
This is a focused code test, not install qualification: the archived tree precedes
this evidence note and final manifest refresh. No code changed after the snapshot.

No model calls, production deployment/restart/messages, private chat, other plugin
or wmw change. No public default model, channel or personal preference changed.
`as_of` remains an expiry reference for current validated advice, not a claim of
full historical control-state reconstruction. Actual ingress identity, exact user
intent and delivery/feedback target binding still require a qualified host path.

Continue semantic feedback interpretation and prospective utility evaluation,
natural expression admission, actual delivery/attributed outcomes, memory/agenda
adaptation, external-memory migration and derived-copy forgetting, rollback and
portable lifecycle/production acceptance. These correctness improvements do not
substitute for an intelligent, useful long-term proactive agent.
