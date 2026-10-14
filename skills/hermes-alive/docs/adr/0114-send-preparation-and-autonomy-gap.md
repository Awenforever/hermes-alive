# ADR 0114 — Send preparation, with the autonomy gap explicit

Date: 2026-10-14

## Composition

Add `SendPreparationRuntime` from current retained planning/expression to existing
send-time authorization and a stable action-attempt identity. The host supplies
the route binding and authenticated confirmation/delegation event identities.
Malformed execution identities are rejected before model calls. Model review
does not supply permission; the wrapper never guesses a target or changes the
body to bypass missing expression authorization.

Silence creates no authorization or attempt. Denied authorization creates no
attempt. Authorized preparation records one owner/selection/expression-bound
attempt through the existing outcome projection. Reopened preparation with the
same canonical permit creates neither a second attempt nor another provider call.
The result always has `sent=False`: preparation is not transport or a successful
delivery outcome. It owns no platform FIFO and launches no external command.

Current authorization is reevaluated even on replay. A changed canonical policy
cannot reuse the old authorization operation; a new operation evaluates the new
policy and refuses preparation when disabled. Existing immutable attempt history
is not rewritten, and no new attempt is created after refusal.

## Critical remaining design obligation

The current authorizer requires exact user confirmation for a model-rendered
expression. This is an existing conservative research restriction, NOT the final
product design for an autonomous Alive. Do not declare completion by installing
a per-message approval assistant instead of the requested proactive intelligence.

Next design explicit, bounded, revocable user delegation for natural expression,
separate from model semantic judgments and source-support assessments. It must
preserve owner, destination, action kind, sensitivity, cadence, current policy,
retained evidence and launch-time revocation checks. Neither a positive review
nor installation alone grants it. Then compose qualified Hermes host delivery
and trustworthy outcome/feedback capture. No production delegation or configuration
has been created by this step, and existing grants must not silently expand.

## Evidence

Windows passes missing confirmation, selection-only confirmation refusal, exact
expression confirmation, provider-free/duplicate-free reopened preparation and
canonical policy disable/replay refusal. Linux
`alive-send-preparation-offline-20261014-r2` exits 0 for this test and the adjacent
expression-runtime regression. Models/grants/routes are synthetic fixtures; no
real provider, private chat, external transport or production restart is used.
Network disabled, read-only scratch mount, 1 CPU/2 GiB/256 PIDs.

Dependency snapshot: ADR-0113 source plus these exact files:

- preparation runtime SHA-256: `8fcb3c4a0fc705d5d7c6b095b9e96213534c76ea19b905da45cc432f1b25e8d2`
- preparation test SHA-256: `19a40928f9cea426cdde4b5b18377f5a87ca103f97d6a2775feb621fa07d1b25`
- updated expression test helper SHA-256: `407c1030728c08e7f456dda152a07a8e6fa0661c24a69c12d7bf1b475931c17c`

Initial Windows/Linux r1 withdrawal assertions expected the old operation to
return a refusal. The existing authorizer instead rejects changed canonical
policy as changed operation semantics. Tests now require that exception, then
verify a fresh operation returns denial. No production check was weakened.
The full runtime still needs autonomous delegation, transport composition,
feedback attribution, actual model quality and production/portable acceptance.
