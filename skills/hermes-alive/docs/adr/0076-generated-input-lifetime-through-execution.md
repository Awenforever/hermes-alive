# ADR 0076 — Generated input lifetime extends through execution

Status: isolated structural regression repaired; real transport and semantic
admission remain unqualified.

## Observed gap

The new opportunity execution test first failed with `stale generated inputs were
authorized`: forgetting an explicit profile input after selection did not prevent
SendTimeAuthorizer from issuing a permit. The original journal event still existed,
so generic event-existence checks could not detect withdrawal. A retained candidate
or agenda copy is not permission to keep using withdrawn original inputs.

## Shared contract

DeliberationSynthesizer now exposes selection-source validation. It checks owner
and sensitivity headers before resolving a frame, requires the current selected
candidate, and reuses the original opportunity recovery validator. That validator
pins the actual source/profile inputs, rather than reselecting today's top-ranked
discovery window. It also checks exact candidate content and original host authority.

SendTimeAuthorizer uses this check before issuing a permit. DispatchOutbox repeats
it after authenticating the lease/contract/route and before recording execution
start, then again after authenticating a live start and before trusted launch.
Projection-capable readers run outside SQLite writer transactions; placing them
inside the route checker would risk nested writer deadlock. Both boundaries accept
an optional context vault, preserving installations with separate profile storage.

A withdrawal after start blocks launch without deleting or releasing that consumed
start. This is not atomic with a network send: qualified host launch must still
address the remaining race and authoritative external result observation. No review
receipt grants authority and no user permission is inferred from model scores.

## Actual local evidence

Windows Python 3.14 opportunity execution suite passes twelve synthetic cases:
clean execution and unrelated source ranking changes; profile forgetting and
source erasure before authorization, before start and before launch; separate
profile-vault clean execution and forgetting at all three boundaries. Positive
cases verify exact content and one start, not a delivery success. Negative cases
before start leave no start; after start retain exactly one consumed start.

Action authorization, CLI execution bridge, dispatch evidence projection and
dispatch migration regressions pass independently. No provider or transport is
called. The fixture supplies USER_CONFIRMED host metadata plus a later exact user
confirmation and test-only authenticated route. It is neither an installed public
default nor evidence of an autonomous delegation design or qualified transport.

## Remaining work

Connect reviewed natural expression to the exact authorized action contract;
resolve material assertions embedded in recommendations without treating every
casual phrase as a provable factual claim. Qualify trusted host launch and actual
delivery/outcome attribution, then longitudinal memory, agenda adaptation and
user benefit. Continue installation/migration/rollback and production acceptance
against the full plan. These tests do not qualify a new release or ten real sends.
