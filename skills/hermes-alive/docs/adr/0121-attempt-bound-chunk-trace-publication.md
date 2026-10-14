# ADR 0121 — Attempt-bound local chunk traces, not delivery outcomes

Date: 2026-10-14

## Implementation

Add closed local trace publication to DispatchOutbox, sharing its existing
authenticated-start/lease ownership gate with CLI report publication. This is
metadata on an existing action attempt, not a second channel FIFO or a new send.

Observer construction may bind an exact action-attempt event and dispatch-start
event. A paired binding is required for publication; diagnostic unbound observers
remain usable but cannot be published as attempt evidence. Client references now
include that binding in their owner/route HMAC, preventing another same-owner,
same-chat attempt from borrowing the trace. Model/user JSON is not a producer;
this API belongs to the trusted qualified host observer.

Publication requires a closed entered observer, the exact owner/route/attempt/
start, bounded sequential reference records, literal coverage flags and ownership
of the authenticated live start. Stored data contains only anonymous references,
counts, coverage flags and local provenance. No raw body, client ID or context
token is persisted. An authenticated structural event binds all fields.

`trace_state` distinguishes closed, interrupted and uncertain-scope traces.
Exceptions, cancellation and pending close are not proof of zero effects or safe
retry. Every state has complete_inventory_proven, external_delivery_proven,
canonical_quote_target_proven and delivery_authority_granted all False. The
canonical dispatch result verifier rejects these local observation events.

Exact serial replay after reopening returns unchanged canonical event/sequence;
conflicting trace data cannot replace an existing record. Cross-process concurrent
publication and final delivery/history transitions remain to be qualified.

## Evidence

Windows tests pass closed and cancelled traces, open-trace refusal, owner/route/
same-chat different-attempt refusal, wrong lease token, unchanged canonical replay,
conflicting replay refusal and canonical-result rejection. No outcome or learned
preference is appended. Existing observer contracts also pass after attempt binding.

Linux explicit current-file module overlay passes the publication tests and four
actual Hermes command/local-sink modes (success/reject/partial/skip), verifying
the extracted shared ownership gate retains the prior CLI behavior. This is not
fresh installed-package qualification. Models, user grants and IO are synthetic.

Final input hashes:

- outbox: `6581603c41f283d8d62525b22671a670008eac3200f77e83a866b62a89e04d75`
- observer: `173766597198f1402454e6f4b6b14ac47d294dc1be51d1dab6bc859bbe93765d`
- publication test: `7f244cb411193ad1eb303c43de7bb88db9b0e5a0073ef362c87cec1f04e02b8a`

Initial local tests exposed a missing regex import and a test comparing initial
AppendResult against replayed JournalRecord wrappers. The import was fixed;
replay assertions now compare exact canonical event bytes and sequence, not
different wrapper types. No ownership guard was weakened.

The container is network-disabled, bounded, explicitly test-labelled and auto-
removed; its process exits 0 and absence is checked. No retry source tree was
created. Production gateway start time is unchanged; there are no real sends,
model calls, private-chat reads or wechat-enhance changes.

Next integrate this publication into a qualified transport producer lifecycle,
resolve shared queued-task ownership without guessing, and connect canonical
delivery/history/quote feedback. Keep authenticated onboarding, bounded scheduling,
actual model semantics, useful longitudinal behavior, migration/rollback and
production acceptance in scope. The full Alive goal remains unfinished.
