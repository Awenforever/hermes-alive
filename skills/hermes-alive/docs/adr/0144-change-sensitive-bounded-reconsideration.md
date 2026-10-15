# ADR 0144 — Wait for change without forgetting to reconsider

Date: 2026-10-15. Status: opt-in isolated integration; not activated production.

## Problem and boundary

The host can open a fresh cycle after every closure. Even a well-founded silence
could therefore spend another model call on the same situation each tick. Internal
expression/action history helps novelty, but is not a scheduler or sufficient
cost control. Conversely, remembering silence indefinitely would turn temporary
circumstances into permanent suppression and miss meaningful new events.

This change is an Alive cognitive reconsideration boundary, **not** a platform
queue, Context Token manager, transport retry timer or permission to resend. The
existing reconciliation tick runs first, including when cognition waits. Pauses
and transport attention take precedence over cached cognition.

## Design

`ReconsiderationStore` records only successfully completed **silence**. Selected,
failed, interrupted, unauthorized and pending actions cannot become a wait. The
host explicitly supplies a reconsideration window (integer 1–3600 seconds) and
configuration identity; default `None` leaves existing behavior unchanged during
qualification. `AutonomousHostRuntime` owns that identity, rather than accepting
an override in per-cycle parameters.

Context uses the current qualified readers for discovery, explicit memory,
learned advisory, generated wording, registered intents/outcomes and literal
feedback. Effective non-callback planning/expression options, owner policy,
execution mode and window also participate. Original message bodies are not read
to detect a new inbound: an owner-scoped input sequence suffices. An owner journal
frontier conservatively wakes on further activity, excluding only host open/close
and the wait records themselves. Foreign-owner activity does not invalidate it.

Upcoming available/due/expiry metadata for active/snoozed agenda items and source
expiry cap the window. Metadata is owner/clearance scoped before reading; a bounded
agenda overflow disables waiting, not a claim that there is no upcoming boundary.
Active/snoozed metadata also enters the signature so a projected transition with
no owner on its transition event still changes the effective context.

The durable private event holds an installation-key HMAC of effective context,
frontier, original operation/selection, fixed deadline and explicit no-authority
flag. It contains no copied source, memory or reply text. Record identity and
payload are authenticated. A copied signed body under another identity is rejected.
This does not provide global physical erasure of previously derived plaintext.

On a matching later cycle, the original expression/planning is revalidated with
provider calls forbidden. Only current verified silence plus unchanged before/
after context yields `waiting_for_change`, distinct from a new silence decision.
It creates no new model decision, intent or send. Missing/erased retained proof
cannot justify waiting: the host's fresh operation may think again, never resume
the old inference. Storage failures do not become an empty successful context.

Wait reuse does not append or extend a deadline. The same original operation
reopens as its original result, not a different waiting disposition, and cannot
refresh its window. Expiry, clock rollback, changed host configuration/window,
policy, new input, effective reader values or journal frontier prevent reuse.
An inbound during inference prevents publication of a wait for the older context.
Owner policy is rechecked against the one actually used for planning.

## Evidence

Windows and network-disabled, read-only, resource-limited Linux pass the composed
fixture: initial silence; repeated unchanged cycles without inference; same-operation
reopen without deadline extension; restart; foreign-owner isolation; inbound and
new-source wakeups; bounded expiry using a synthetic clock; pause/resume; erased
retained proof; host-owned cycles; configuration changes; clock rollback; invalid
boolean window; inbound during inference; explicit-memory and source erasure
without a new journal sequence; transport attention priority; failed model run
with no implicit second call; agenda snooze/due cap; and signed-body alias refusal.
Model-call counts are independently asserted. Host lifetime/identity regression
also passes Windows. Linux adjacent host identity, route preflight and review
recovery fixtures pass. No real model or actual channel was invoked in these tests.
The existing composed cycle test also passes Windows using read-only frozen
Enhance fixtures and fake physical IO: default-disabled reconsideration preserves
queued submission/replay/shadow/silence/pause behavior. No Enhance source changed;
this is not a real-channel or current Qoder-release interoperability proof.

The first fixture exposed non-JSON frozenset policy serialization; runtime now
normalizes the explicit side-effect set canonically. Later fixture failures were
an incorrect agenda outcome expectation/API use, not runtime passes. The first
Linux wrapper lacked retained transport reconciliation dependencies and failed
before testing; explicitly overlaying those existing Alive modules fixed setup.
These are module overlays over retained dependencies, not new installations.

## Remaining work before activation

- The host must derive/rotate configuration identity when inherited model routes,
  callback semantics or cognition implementation changes. Python callback identity
  is intentionally not guessed or treated as a configuration certificate.
- Window is a host cost bound, not a model's semantic judgment of “later”, a user
  deadline or a learned preference. Connect model-reasoned deferral to persistent
  agenda and event-sensitive wakeups without keyword parsing or repeated babysitting.
- This synchronous current-reader capture is not a proven atomic multi-vault
  snapshot or long-history performance qualification. Cross-process ownership,
  installed lifecycle, bounded cooperative lifetime and shutdown still need joint
  failure testing before automatic operation.
- Commitments affect wake deadlines; this does not prove they are fully integrated
  into planning, prioritized or fulfilled. Source-scope correctness, meaningful
  reflection/learning, layered/external memory, complete privacy/forgetting,
  portable installation, migration/rollback and production ten-clean acceptance
  remain part of the original objective.

No production/Core/Enhance/model/network changes, restart, release or deployment.
Actual-model totals remain 167 logical / 180 observed HTTP starts; actual sends zero.
