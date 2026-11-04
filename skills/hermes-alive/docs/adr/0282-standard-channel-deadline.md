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
