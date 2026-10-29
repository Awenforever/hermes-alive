# ADR0275 — Claim a comparison operation before model IO

Date: 2026-10-29 (Asia/Shanghai).
Status: candidate; not production acceptance.

An additional semantic-store check exposed a real pre-existing defect: calling
the low-level comparator twice with the same operation ID incurred model calls
again before an immutable-record conflict rejected the second execution. The
ordinary expression runtime already guarded its recovery path, but that did not
make the underlying operation safe for another caller or process.

The actual comparator entry now claims its existing durable start atomically.
The journal's unique event identity decides the winner. A previous or concurrent
start refuses another execution before model IO, irrespective of completed,
failed, cancelled or unresolved outcome. There is no implicit retry. Inspection
can still read the original authoring clock without acquiring execution rights.
This reuses the existing journal and operation identity; it adds no queue,
scheduler, provider retry or execution permission.

Do not retrofit an old unresolved start into evidence that nothing happened.
An explicitly new operation still needs the existing current selection, owner,
source, model budget and authorization checks. A claim establishes ownership of
this attempt, not factual quality, a successful outcome or delivery authority.

Verify same-process and cold duplicate calls spend no additional inference,
plus a real multi-process race with exactly one durable winner. Preserve ordinary
success, provider failure, cancellation, supersession and bounded protocol-repair
tests. Re-run affected broad qualification; the earlier citation-only baseline
does not cover this additional runtime change.
