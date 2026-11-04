# ADR 0282 — Enforce the standard channel deadline at submission

Date 2026-11-04. Development candidate.

An installed Ubuntu test profile reached a durable dispatch start, then ran
out of its 30-second authorization window before calling the local adapter.
Profiling showed repeated reconstruction of the selected source evidence and
the original negative review. The profile run measured about 14 seconds in
one start validation. Profiling adds overhead, and a separate unprofiled run
also ran out of time before submission.

Keep the existing authorization window and recheck the lease and execution
deadline after the final synchronous verification. A start that has expired
at that point must stay consumed and must never enter the adapter.

When building a discovery expression context, reuse the completed synthesis
validation already performed by selected-draft resolution in the same call.
Keep the exact sensitivity requirement and read the retained source window
as before. Separate verifications still observe current evidence and policy.

The controlled regression advances the clock inside launch validation and
checks that no adapter submission occurs. Repeat the installed native test
without profiling to measure whether further work is needed on verification
cost. Whole-chain and production acceptance remain open.

## Follow-up after the installed Ubuntu run

The first reduction still left the unprofiled run beyond the deadline in
continuity preparation. Build final-review mode from the original synthesis
already authenticated by the review snapshot. Continuity capture selects
its retained references from the same source window and focused read IDs
as expression authoring, without rebuilding the full authoring context.
These reductions are local to one synchronous operation. A separate launch
check still revalidates current evidence and authority before adapter IO.

On the next installed run, continuity completed and the final check found
that the lease had expired. For the native continuity binding on the same
journal, let the store's own full check guard capture. A generic callback
still gets a full preflight before it runs, and every path retains the
independent final check and deadline guard before submission.

The subsequent Ubuntu run finished the final validation about 2.5 seconds
after expiry and the submission guard refused it. Recover the evidence and
context once per review snapshot, and pass the already validated original
source window to authoring and continuity inside their own synchronous call.
The snapshot shape and stored digest contract stay the same. No recovered
context crosses a host callback or a separate verification boundary.

The prepared-send wrapper used the authorization window to reconstruct
the final review immediately before the outbox reconstructed the same
review at start admission. For permits carrying a final-wording witness,
the wrapper now checks the exact authorization, review, and expression
identities. The outbox still verifies current support before consuming
the start and at the launch boundary. Prepared actions without a bound
witness retain the wrapper's full verification.

Inside each final-review check, use the original expression fields and
wording already authenticated by reconstruction of the review snapshot.
The correction proof still binds the prior expression, exact text digest,
proposal, and reconstructed result. The authorizer only queries whether an
expression requires a review when it has no witness to verify.
