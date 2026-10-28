# ADR 0273 — Current owner contact changes and stale-intent fencing

Date: 2026-10-29. Status: controlled Core, dispatch and portable checks pass; full acceptance pending.

## Problem

ADR0272 separates private task work from contacting the owner, but creation is
not the last owner decision. A person may ask to stop updates and later permit
them again. Treating a new sentence as advice to a communication model leaves
an already prepared message unaffected. Re-enabling the old boolean alone can
also make that stale message appear eligible again. Neither behavior follows
the owner's current intent.

## Decision

Use the existing current-owner `revise` operation, exact item version, evidence
span, guided revision grant and protected source receipt. `notify_owner` is an
optional boolean revision field. Omission preserves the existing choice; it is
not an instruction to revert to the creation default. A stale version or a
nonboolean is rejected before an amendment is admitted. Main-agent interpretation
still has to distinguish a current request from quotations or ambiguous intent.
No new per-item confirmation is demanded when the guided revision grant already
permits this operation. Without that grant, the existing setup boundary remains.

Classify a contact-only change from authenticated previous/current task contents
and unchanged deadline at admission, not from a model-provided flag or words in
the request. Sign that host classification. Work guards can then preserve an
already admitted execution across contact changes without reading new bodies
inside metadata-only status checks. A combined task/deadline and contact change
still fences old work. Older unclassified revisions keep their old semantics;
do not reinterpret history or restart previously fenced work automatically.

Sign an explicit choice in the revision receipt, separately from interpreted
task text. An unrelated description revision cannot grant contact. Creation
replay cannot change the old choice or create a duplicate. Preserve retention,
task state and ordinary execution constraints; permission to contact is never
permission to execute, and revocation does not erase private work or its results.
The source lookup labels the original contact choice as original, so the main
agent cannot confuse it with the effective current choice.

Communication evidence is bound to the latest verified contact revision. For
an item with Core work, use the later of that contact revision and the current
verified work observation. This retains work progress while ensuring that a
stop/regrant cycle changes the evidence identity. Existing recovery and final
adapter-launch validation therefore refuse an old prepared intent even after
contact is allowed again. Ordinary private reasoning keeps its task view.

Validate the amendment's protected authority and retained owner source. An erased,
unavailable or expired source cannot grant contact merely because interpreted
details still contain `true`. Restrict contact without destroying the task.
Old original-source erasure must not be healed by a later contact flag. A choice
to decline original-body retention remains distinct from erasing previously
retained material. No new model router, executor, channel queue or retry path is
introduced. Wechat Enhance retains FIFO/token ownership.

The final validation applies before submitting to the adapter. It cannot recall
messages already accepted into a platform's physical queue; do not imply such
a cancellation or replay historical messages on regrant.

## Required evidence

Exercise both literal-confirmed and delegated task origins. Cover stop, omitted
field, fresh regrant, stale version, malformed field and erasure. A prepared
message must fail both recovery and final launch after stop and after regrant,
with a positive launch check beforehand. Control the lease clock so expiration
cannot masquerade as successful revocation. Use actual Core confirmation,
main-turn collection and registered tool dispatch as a separate integration
check. Also require an actual admitted Core job to finish its original file
effect after contact is regranted and stopped, while ordinary goal revisions
continue to block outdated effects. These deterministic controls are not real language-understanding,
physical delivery, fleet or whole-kernel acceptance.

## Bounded qualification

Canonical347 passed the pure contact-scope and final-launch controls. Its new
Core test fixture omitted `install-runtime --engine kernel`; the resulting
context rejection remains a fixture failure. With the normal install step,
actual Core intake/revision passed on349. The additional real queued-work case
then exposed a functional failure: after changing contact twice, Core reported
completion while the required output file did not exist. That failed result is
retained; agenda state alone was not sufficient evidence of work continuing.

Canonical351 derives and signs the contact-only classification. Actual Core
controls then passed: the original queued work wrote and read back its file
after regrant/stop, and its prior work authority remained valid. Ordinary
before/after/deadline revisions still passed their stricter work fences and
cold checks. Both explicit-confirmation and delegated contact origins passed
recovery and final adapter-launch revocation, including regrant and erasure.
Actual Core registered tool dispatch rejected stale versions, nonbooleans and
the reserved host-classification field. Omitted choices preserved the scope.
Three native reminder variants and old/new memory-grant controls also passed.
Original351 terminal0, Docker die/destroy1793225131 and CID absence were checked.

Broad portable352 on the same351 runtime passed, with original terminal0,
die/destroy1793226117 and CID absence. It retains the explicit runtime-only
acceptance limit. Obsolete broad348 was intentionally stopped after preserving
partial logs, because349 required a new runtime candidate; it is neither a full
pass nor a product failure. No production changes, real model calls or physical
messages occurred in these controlled scope/work checks.
