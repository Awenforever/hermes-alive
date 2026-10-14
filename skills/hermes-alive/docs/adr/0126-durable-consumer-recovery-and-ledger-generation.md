# ADR 0126 — Durable consumer recovery and ledger generations

Date: 2026-10-14

## Implementation

`TransportPublisherConsumer` reads one bounded publisher page, persists the
existing canonical observations and only then checkpoints consumption progress.
The checkpoint is authenticated and binding/owner/sensitivity-scoped, references
the exact authenticated observation IDs and carries the last publisher sequence.
Head reconstruction checks each referenced observation and refuses missing,
mis-scoped, reordered or noncanonical evidence. An untrusted latest checkpoint
is not silently skipped to an older convenient cursor.

The writer's transaction checks that the previous progress is unchanged. Two
consumers with different page bounds cannot fork the checkpoint head: the stale
writer must reread, without sending. The bridge's event factory now retrieves
canonical replay under the journal writer lock; different wall-clock invocation
times no longer cause a same-observation insertion race. Factories/preconditions
perform only same-connection reads, canonical JSON and in-memory HMAC checks;
they do not call the external publisher or acquire another writer.

After an interruption between observations and checkpoint, reopen replays the
same observations and advances progress without duplicates or another send.
Empty pages do not create endless checkpoints or imply no effects/completion.
If publisher write health is false, known reports may enter the journal but the
consumer cursor stays put; recovery rereads rather than silently skipping loss.

Publisher branch `feat/alive-transport-evidence`, commit `95138df`, adds a persistent
random database epoch and AUTOINCREMENT high-water sequence. Pages read metadata
and rows in one SQLite read transaction. The Alive binding and observations now
include the epoch; changed epoch, high-water behind the cursor or rows beyond the
high-water refuse qualification. Reopen preserves the epoch. A reconstructed
database cannot silently resume an old cursor just because its path/source match.
Old experimental bindings lacking an epoch are not silently amended.

This is a bounded synchronous consumer API, not a registered background scheduler,
new queue, transport retry, acknowledgement of the dispatch or feedback learner.
All reports/checkpoints keep coverage uncertain and deny delivery/inventory proof.

## Evidence

Windows fake IO and Linux actual stock Weixin constructor/send with only physical
IO replaced exercise the real kernel start and enhance publisher: interruption
after journal observation before checkpoint; reopen without duplicate records;
later ACK; empty poll without a new event; unhealthy nonempty page freezing the
cursor and healthy replay; false-owner checkpoint refusal; changed epoch; observable
same-epoch counter rollback; and two barrier-synchronized competing consumers with
different page limits, exactly one checkpoint winner and successful reread.
Physical send counts remain unchanged by all polls/recovery/competition. One
dispatch start and no canonical delivery outcome remain. Bridge/prepared-send
composition and existing enhance producer/FIFO/model/context/retry tests are also
regressions, not proof of user utility or production delivery.

Linux final process exits 0, read-only current-file overlays, network none plus
audit guard, bounded resources and --rm. No labelled test containers remain and
production StartedAt remains `2026-10-11T07:43:25.630569081Z`. No extra full source
snapshot/clone, real model call, real channel send or private-history read occurred.
Both repositories remain development-only; no production restart/deploy/release.

## Not yet qualified

Epoch/high-water checks do not detect every coordinated restore or malicious
database rewrite. Full state migration must preserve/explicitly reconcile both
sides; reader upgrades require qualification of historical bindings rather than
silent cursor reset or rewriting old evidence. A crash after physical IO before
the producer's local commit remains ambiguous. Missing/pruned reports cannot be
interpreted as zero effects, and producer records still are not cryptographic
remote delivery or canonical quote evidence.

The latest checkpoint's authenticated page is checked, not an unbounded replay
of the entire ancestral chain on every poll. Whole-page observation ingestion
still is not one transaction. Synchronous IO, writer shutdown, performance,
bounded subscriber lifetime, authenticated controls/consent and the new send
entry's adverse cancellation/publication behavior require further qualification.
Next connect bounded autonomous scheduling and ambiguity/finality/feedback while
retaining these operational safeguards; real-model longitudinal usefulness,
portable installation/migration/rollback and production acceptance remain open.
Enhance's final independent release/acceptance stays deferred until Alive.
