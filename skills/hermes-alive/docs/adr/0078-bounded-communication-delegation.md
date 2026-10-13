# ADR 0078 — Bounded user delegation is separate from discovered agenda

Status: isolated communication permission path implemented; onboarding, quality
admission and actual automatic delivery remain unqualified.

## Structural issue

USER_DELEGATED candidates were authorized only when their agenda item itself had
USER_EXPLICIT authority. A discovery opportunity correctly has observational
provenance, so this conflated permission to share with who discovered the item.
Relabeling every discovery as user-authored would corrupt the event history;
requiring approval of every new message would defeat the proactive product goal.

## Explicit permission scope

ActionDelegationStore records a self-authorized, authenticated grant separate from
discovery and selection. Scope includes owner, exact current autonomy policy event,
exact route binding, channel-send capability, allowed SHARE/ASK kinds, maximum
sensitivity and an explicit expiration no more than thirty days away. No model
score, learned preference, source topic label or relevance judgment grants permission.
Topic relevance remains a cognition/personalization decision rather than an
unreliable keyword-based authority boundary. Tool execution is not covered.

SendTimeAuthorizer accepts a grant identity for original USER_DELEGATED authority;
it cannot upgrade NONE or substitute for a confirmed-expression approval. The
original candidate and original input provenance remain unchanged. Permit recovery
binds that identity and rechecks its current scope. Dispatch route checks repeat
grant validation during reconciliation, authority refresh, start and pre-launch.
These grant checks are read-only and can run inside existing writer transactions.

Revocation is a separate retained event; the grant is not deleted or rewritten.
Expired, revoked, foreign, route-mismatched, policy-mismatched, wrong-kind,
over-sensitivity and forged grants are unusable. An unusable revocation marker
fails closed rather than picking a convenient historical grant. Current autonomy
policy and qualified host route checks remain mandatory independently.

## Actual evidence

- Windows Python 3.14 full opportunity execution suite passes 24 synthetic modes:
  the previous 16 plus delegated clean execution, revoke before authorization,
  before start, before launch, before permit replay, wrong route/kind/clearance.
  The delegated authorization call passes no per-message confirmation ID.
- A separate delegation suite checks owner/policy/route/kind/sensitivity/capability,
  future/expired time, tampered grant refusal, foreign create/revoke refusal and
  retained original history after revocation. Initial test compared AppendResult
  with JournalRecord; that fixture assertion was corrected to compare immutable
  event and sequence, not hidden as a runtime defect.
- Existing authorization, outcome projection and dispatch evidence regressions
  pass locally. No real model or transport is called.
- Immutable input tree `737f02c2b0ce6771bd4fa486a42f84f79fb9f4c9`, archive SHA256
  `04ea3526e234fe54deaf40f70ed72efb1ad8a872029e6503b8cbcbb5a87aba69`.
  Network-none `alive-delegation-offline-20261013-r1` exited zero, started
  `2026-10-13T13:52:51.19437437Z`, finished `2026-10-13T13:53:10.757036885Z`.
  Log SHA256 `53d0a3c92e47c730150d1ed51c9b133179e37babeeafd3d60f20e7eee4e6b05f`.
  Delegation, full opportunity execution, authorization and CLI bridge suites pass
  in the managed Python 3.13 carrier. Only owned test scratch is mounted, read-only;
  no production volume or network is available. Later docs/manifests are not that
  tested input tree. This is not a full installation or qualified gateway test.

## Still required

The grant API is a trusted-user-command boundary, not proof of authenticated real
gateway ingress or a shipped onboarding flow. No public default grant is enabled.
Permission is not quality: uncertainty/source support, semantic fidelity, relevance,
interruption budgets and bounded cadence must still govern autonomous admission.
Natural-expression automatic admission remains blocked; explicit confirmation from
ADR 0077 is not silently replaced by a grant. Actual launch, delivery/result
attribution, user feedback and longitudinal agenda/memory adaptation remain open,
alongside migration, derived-copy forgetting, rollback and the full acceptance
matrix. No deployment, release, real send or ten-call acceptance follows here.
