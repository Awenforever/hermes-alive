# ADR 0156 — Private native worker protocol and actual Hermes fallback

Date: 2026-10-16. Status: opt-in caller/worker implemented; controlled-HTTP Core proof.

## Connect the previous components rather than another prompt experiment

NativeWorkerCaller implements the existing async ModelCaller shape through
ManagedModelProcess and a dedicated native_model_worker.py entrypoint. The child
runs actual Hermes AIAgent, prompt assembly, provider SDK and official plugin
lifecycle dispatch; scoped completion evidence binds the returned text/model.
There is no automatic production hook, daemon, model-setting write or send.

The host explicitly supplies owner, parent operation, managed interpreter/Core,
private root, scoped environment, a consented identity snapshot, current-binding
check, and a Hermes runtime-resolution callback. Empty model selection is forwarded
as None; a configured alias is forwarded unchanged to that callback. Alive does
not invent a default model, search provider lists, add a credential, or substitute
its own fallback. The callback returns a fresh finite JSON API capability, including
the already-resolved fallback chain; Core itself performs request-time fallback.

This is not yet an automatically assembled gateway/profile resolver. Host callback
tests below use explicit synthetic capabilities. Real host-scoped resolution,
credential-pool/OAuth renewal, provider policies and all API modes still need
admission. Non-JSON/callable credentials, unresolved fallback credentials and
CLI/ACP routes are explicitly unsupported, not silently downgraded. No claim that
all configured providers or all devices are production-qualified follows.

## Protocol and privacy

One version1 input binds parent operation, fresh request nonce, subject, task,
exact system/user-message digest, trusted runtime/identity snapshot and generation
budget. The whole canonical request has a digest. Messages stay untrusted task
data; they cannot rewrite the separate host routing capability. Reserved model,
tool, input and token-budget overrides (including extra_body) reject rather than
letting a request override the worker's text-only boundary.

The child accepts only an empty parent-owned workspace. It constructs a minimal
private Profile/home/cache/shared-runtime, with no foreground sessions, memory
manager, user files, channel configuration or arbitrary plugins. It loads only
its packaged completion observer, disables tools/background review/compression,
and adds the caller task as an ephemeral native prompt alongside optional SOUL.
The worker Profile is a processing capsule, not a migration copy of user state.

Prompts/runtime credentials go through bounded private stdin, not argv. Core
stdout/stderr are discarded in-process; exactly one bounded JSON protocol document
is emitted. Failure returns a static class and, for completion-contract failures,
bounded structural counts/static errors, never provider error messages or partial
model text. Parent failures do not forward raw worker stdout/stderr. This is not
secure erasure: temporary handles and Profile files are protected but unencrypted.

The parent accepts only exact nonce/operation/owner/request/context binding,
current host binding before/after execution, matching normalized text/hash and
scoped model evidence. Semantic quality and action authority remain false. Changed
bindings, foreign results, mixed generation text, old evidence contracts, malformed
protocols or failure exit reject, even if a response was computed. A completed
process is not proof of a correct contribution.

Pending/uncertain workers retain their lease and private workspace; another call
on that caller is denied until the original lease closes. Cleanup is attached to
the retained supervisor, not TemporaryDirectory garbage collection when an awaiter
goes away. Reaping does not restart a worker. Parent-crash/event-loop destruction,
OS-level descendant containment and restart adoption remain ADR0155 gates; this
protocol does not solve them by claiming a checksum is process authority.

## Actual Core exposed an incorrect v1 evidence assumption

Initial controlled tests pass primary and configured-alias routes, but fallback
fails with NativeCompletionError. Structural evidence shows api_calls=1, one
logical API identity, an explicit failed attempt, then a pre-request with a changed
route. Core reuses that logical request ID across fallback. The old observer treated
the next pre-event as a conflicting replay. Do not patch Core, drop the check, or
take a global last model to make it pass.

Completion evidence is now explicitly `hermes.native.post_api_request.v2`:

- Logical coordinates remain turn/api_request_id; the official events' exact
  started_at value identifies an attempt within that logical slot.
- The start value is used for equality only, never time windows, age, ordering or
  guessing. Clock rollback does not invalidate an otherwise distinct marker.
- Explicit failure terminates the preceding attempt; a new attempt may then use
  the same logical coordinates. Overlap, missing markers or conflicting reuse
  rejects. Identical pre/post redelivery remains idempotent.
- Final evidence includes attempt ordinal/start marker and comes from that exact
  completion's response-model label, route and text hash. All other attempts must
  be failed, not merely unfinished. Native attempt bounds remain finite.
- Turn api_calls is checked against logical request identities, not native attempts
  or physical SDK HTTP retries. Those three counts must not be conflated.

Old v1 evidence is not reinterpreted as v2. It was ephemeral development evidence,
not an installed production database migration. The protocol rejects an old-contract
result under a new operation. No SHA-based Core compatibility gate is introduced.

## Verification actually performed

Native Windows uses real child processes with a controlled protocol worker, not
real Core: default/alias forwarding, preserved fallback snapshot and identity,
nonce/context/text/authority/version rejection, nonzero and non-JSON exit,
pre/post-current-binding denial, call budgets, repeated cancellation during delayed
startup, no duplicate spawn, retained files and eventual cleanup. This is not
Windows Hermes/provider qualification. Pure completion tests add same-ID fallback,
backward start markers and the prior concurrency/privacy/lifecycle cases.

The isolated Linux test uses actual retained Core and actual production worker
entrypoint, with a **test-only operator bootstrap replacing physical HTTP**. No
test mode or mock injection is added to the worker protocol. It verifies:

1. Default selected capability reaches the actual API request with correct key.
2. An existing alias selects its host-resolved capability without configuration writes.
3. A synthetic403 on primary invokes Core's declared backup, with its own key/model;
   the final response label is backed by v2 scoped evidence, not the primary alias.
4. Canonical Alive discovery/attributed-feedback context traverses the same worker
   into the existing AutonomousCycleRuntime shadow path; reopening that exact
   completed operation spends no additional worker call or native API request.
5. Native identity/task/context reach the request, tools/streaming are absent, and
   private workspaces are empty after observed terminal exits.

Controlled HTTP means synthetic permissions and replies, **not live fallback health,
intelligence, independent review, provider billing/cancellation or production
quality**. Full replay is tested only for the current completed shadow operation,
not cross-restart OS worker adoption. The resolver callback is a fixture, not proof
that installation correctly auto-constructs a real profile capability.

Source hooks copy recursively in the lifecycle implementation, but no fresh installed
device/lifecycle qualification is inferred from reading that code. Actual cumulative
model use remains290 logical/304 observed async HTTP starts; new real calls/sends0.
No production/Profile/Core/Enhance/model/network change or main release follows.

## Next whole-objective work

Construct/qualify the host-scoped Hermes capability projection without copying an
entire Profile or dropping configured routing/privacy/presentation policy. Then
run actual configured models on new sustained shadow scenarios through this real
worker boundary, comparing direct native contribution with the existing plan path.
Do not adopt the intermediate purpose layer or direct wording path rejected by
ADR0151/0152 merely because the process protocol works.

Connect useful selection/expression, retained memory/agenda and attributed outcomes
to cautious reflection learning; qualify external Halo, full erasure, migration/
rollback, cross-device install/upgrade/reinstall and production acceptance. The
full long-lived objective and Qoder's Enhance/FIFO/Token ownership stay unchanged.
