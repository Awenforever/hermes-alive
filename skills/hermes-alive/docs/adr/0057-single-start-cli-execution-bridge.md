# ADR-0057: Single-start CLI execution bridge

Status: bridge and journal-authority recheck implemented; runtime launcher unqualified

## Decision

Connect action admission to text compilation and process observation without
letting process results become delivery or benefit claims. The operator-bound
`execute_text_cli_once` bridge consumes a real outbox start, compiles only its
authorized content/route, rechecks the start immediately before calling the
trusted launcher once, and records the returned structural CLI observation.

`validate_execution_for_launch` checks the authenticated start, current outbox
ownership, lease generation/token, execution window, current autonomy policy,
current route and host contract, and exact authorized body/route. It catches
policy events whose journal append preceded materialized projection update by
projecting through an observed journal head before checking policy. It cannot
atomically couple local authorization to an external network side effect:
concurrent revocation, qualified runtime identity and process launch are still
executor/host integration obligations, not guarantees supplied by this method.

Exceptions propagate without releasing or retrying a consumed start. A timeout,
launcher error or journal-write error can occur after an external effect. Even
compilation refusal after start remains conservatively consumed rather than
automatically reusable. A future proven-no-launch recovery path must be explicit;
do not turn exceptions into zero-effect evidence. The bridge never acknowledges
an attempt and never fabricates a terminal receipt.

## Evidence

- The recovery fixture now runs a real authorization/lease/start through the
  bridge using a synthetic launcher and parsing callbacks. It verifies one
  launcher call, refusal of repeated execution, changed content/route rejection,
  expired-window rejection, and a nonterminal observation. Existing recovery,
  privacy, receipt-integrity and ambiguity assertions still pass.
- Separate bridge tests exercise compile refusal, launch timeout, guard refusal
  and observation-write failure. They prove control-flow ordering and no retry
  in fake-capability isolation, not production authorization or real delivery.
- Dispatch migration, evidence projection and action authorization regressions
  pass. Actual current-source command parsing remains covered separately by
  ADR-0056; these separate tests are not yet a combined real-process bridge.

## Next qualification

Implement the operator-owned launcher against the actually selected Hermes
runtime/profile, with qualified identity/environment, bounded process capture,
crash/timeout evidence and no shell. Exercise that launcher with discovered
local platforms before requesting any live canary. Obtain actual external
channel receipt semantics and human/longitudinal usefulness evidence. Preserve
all production migration, rollback and privacy requirements. No live transport
is installed or activated by this bridge.
