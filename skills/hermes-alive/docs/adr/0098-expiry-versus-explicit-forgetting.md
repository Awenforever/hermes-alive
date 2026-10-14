# ADR 0098 — Historical retention must not bypass explicit forgetting

Status: erasure provenance prerequisite implemented; delivered archive not yet connected.

## Why a history copy alone would be unsafe

ADR-0097 separates actionable-intent lifetime from consented delivered history.
Inspection finds that erase_expired used erase_item, making automatic expiry and
explicit user forgetting indistinguishable in the durable erasure ledger. An
archive reader could not safely distinguish permissible independent history from
a derivative that must be forgotten. Do not introduce an archive that ignores all
original-content tombstones or silently interprets old tombstones as maintenance.

## Minimal general provenance change

Automatic expiry now records an expiry selector; explicit item and subject
erasure retain their meanings. The same exclusive-operation, transactional delete,
resumable completion, vacuum/WAL handling and affected-backup purge are used.
No expired plaintext is restored, deadline extended or backup preserved by this
classification. Unknown erasure selector kinds are rejected rather than accidentally
treated as subject selectors.

The read-only explicit_erasure_recorded query checks any non-expiry tombstone for
a dependency, without resolving its content. Callers must verify owner and scope
first. Old item tombstones have unknown origins and remain explicit deletion.
An explicit erase_item after expiry creates its own tombstone even when the
ciphertext is already absent; expiry must never consume the user's later request.
This is local erasure provenance, not cryptographic protection of the ledger or
proof that every derivative has actually been erased. Those remain required.

The focused Windows vault suite now verifies physical expiry erasure, expired-read
rejection, expiry not labelled as explicit forgetting, and explicit forgetting
after expiry being preserved. Existing erasure/backup/concurrent tests remain.
Initial Linux regression setup includes nonexistent privacy/coordinator filenames;
that invocation must not be reported as a passed batch. Corrected results are
recorded after authoritative terminal verification. Corrected container
alive-erasure-reasons-regression-20261014-r2 is verified exited 0, from
2026-10-14T01:39:40.56231729Z to 2026-10-14T01:40:37.720982525Z. All eight
existing suites pass: content_vault, retention, memory, feedback_synthesis,
feedback_recovery, learning_context, source_epoch and opportunity_execution.
The fake recovery-call counter is not a new real model call. This is a focused
erasure/dependency regression, not archive functionality or production acceptance.

## Next actual delivered-history contract

The next archive boundary must require a canonical delivered outcome and its exact
signed start/result chain, scoped attempt and executable-contract binding while
the original text remains available. CLI success/partial/skip reports are not
delivery proof. Explicit outbound retention consent must predate the capture;
inbound-only consent cannot authorize a copy of sent text. The archive must retain
exact text, delivery/attempt/consent dependencies and its own bounded expiry, not
extend the expression's execution authority. Repeat observation cannot refresh
retention. Explicit forgetting/revocation must invalidate or erase derivatives.

No retrospective reconstruction of already expired text is allowed. Actual host
receipt qualification, user quoting/feedback attribution, archive-to-feedback
integration and learning approval remain unfinished. This prerequisite is not
claimed as a working delayed-feedback feature or a narrower replacement goal.

## Evidence and scope

Runtime/test staged tree 96474e745558c20b5f83b0ac30965d755b37424a; archive SHA256
de2dcafcc5122e2dd7a25e7ab1a5f480e020669237dd120b8ab8eafd189e0e58.
No real model/HTTP calls; totals remain 95 logical / 107 observed HTTP attempts.
Only disposable synthetic content is deleted in these tests. No production data,
container, config, model, authorization or gateway restart change; no wmw or other
plugin changes, private-chat access or credential export. Production acceptance,
full layered/external memory, sustained agenda, useful feedback/adaptation,
migration/rollback and portable installation/lifecycle remain required.
