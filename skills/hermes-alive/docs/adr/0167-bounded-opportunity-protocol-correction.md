# ADR0167 — A model corrects an invalid protocol response, once

Date: 2026-10-18. Status: implemented; production qualification incomplete.

## Why

ADR0166's real native r2 produced a relevant candidate but omitted the final JSON
brace. The operation correctly failed with ModelJSONError. Appending punctuation,
guessing fields or treating a rejected response as a usable draft would erase the
distinction between model output and accepted evidence. Starting new cycles until
one passes would hide repeated spend and failures.

## Contract

Within a new opportunity interpretation, one initial ModelJSONError may request
one model-mediated correction. Only JSON parsing failure qualifies, not provider
failure, cancellation, changed/erased evidence or an oversized response. Invalid
candidate fields remain separately rejected under the existing contract; this
change does not silently manufacture missing schema values.

Before the second call, preserve the initial invalid response and actual model
label in the owner-scoped encrypted content vault with bounded source/feedback
retention. The journal records its content reference, prompt digests, original
operation cause and an explicit non-authorizing recovery event. It stores no raw
failed text in plaintext. The original sources/context and untrusted failed output
are given back to the model; the model must return a complete response, not a
suffix or a code patch. The final model label belongs to the correcting response,
not the first generator. Existing host/Core model resolution remains authoritative;
there is no plugin-owned fallback registry or production model change.

Both calls share the original timeout budget. Current sources, commitments,
explicit memory, feedback, learned context, expression/action history and revision
context are checked before and after every call. A real revocation stops work,
including correction. The stage remains non-executing and does not grant authority.

There is at most one correction event per operation. A second invalid result,
timeout, cancellation or error leaves the operation terminal. It cannot be respent
by calling run again or continuing an unknown background request. Old terminal
failures are not changed into success. protocol_recovery=False explicitly disables
the extra call; invalid option values are rejected before model access.

Retained completion checks require the correction event's original owner, source,
sensitivity, cause, chronological position, prompt binding and protected invalid
response. It reparses the retained failure to confirm it really was invalid JSON.
Hiding a correction behind protocol_recovered=False or deleting/erasing its
evidence makes completion unrecoverable; a status flag alone is not proof.

## Evidence and next qualification

An isolated offline test covers successful model correction, two invalid results,
explicit disable, provider error, revocation before/during correction, cancellation,
shared-budget timeout, repeat-spend denial, tampered recovery labels/context and
protected failure text. Opportunity/context synthesis and source-support history
also pass in that isolated run. These are synthetic model responses, not genuine
provider correction or recipient satisfaction evidence.

Real r3 completes five native calls, all actual Qwen3.8/custom:ustc. Baseline
abstains, A proposes the bicycle reference, explicit replacement B and reopened B
propose gardening, and withdrawing B returns to abstention. All retained results
load without inference; none needs protocol correction. This is interpretation-
only evidence, not ten error-free autonomous full-chain rounds.

Real r4 explicitly injects the exact prior r2 malformed response, verified against
its retained native content fingerprint. It is labeled historical fault replay,
NOT a fresh generation call. Only interest A runs. One new actual native
Qwen3.8/custom:ustc call corrects it against current original evidence; the complete
candidate is admitted, protocol_recovered=True and completion reopens without
inference. Two stage invocations comprise one replay and one fresh model call,
not two new model calls. Pending workers0, action/authorization/dispatch/sends0.
Both containers terminated and their exact model-only projections were removed.

The first broad regression exposes a diagnostic contract problem: the existing
four-case action-history fault probe had not disabled recovery. Its positional
fault injection counted the correction as another scenario and overwrote
single-response fields. It now explicitly opts out of recovery and records calls
individually; the original four-call/failure assertions pass without loosening
them. The new protocol test and native r4 exercise recovery separately. Failed
broad-run logs remain retained; the corrected tree requires broad rerun.

The native interest probe now has an explicit maximum of ten logical calls for
five phases (one correction maximum per phase), and reports recovery provenance.
Broader regressions remain required; successful comparisons and correction do
not qualify the complete discovery-to-delivery-feedback loop.
Personalized discovery recall, diverse accessible sources and deployment/migration
remain open under the living plan.
