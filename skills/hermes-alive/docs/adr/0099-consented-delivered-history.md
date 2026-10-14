# ADR 0099 — Delivered-history lifetime is not executable-intent lifetime

Status: isolated history and delayed-feedback composition; real host capture and
learning/production qualification remain open.

## Implemented boundary

DeliveredHistoryStore captures an exact channel-send contract only while its text
is still available and its authenticated binding matches the original authorization.
Capture requires a canonical delivery_succeeded outcome, validated signed start/
result chain, scoped attempt and authorization, and current explicit outbound
retention consent that predates the receipt. A model candidate, CLI report or
partial/skip/error result is not a delivered outcome and cannot authorize capture.
The host authenticity of actual receipt producers remains a separate requirement.

The encrypted history has its own non-executable purpose. Its signed event binds
the canonical receipt, attempt, authorization, consent, content reference and
deletion dependencies. Execution and learning authority are explicitly false.
Expiry is bounded by receipt observation time plus the consented retention days;
repeated capture uses the same receipt/start identity and cannot refresh retention.
Scoped verification rechecks signatures, current consent generation, exact contract
binding and own expiry before returning text. A revoked or changed consent is not
silently bypassed by falling back to the old executable copy. Future-dated receipts
are rejected. Orphan content from a failed/conflicting append is removed, while a
concurrent winning record is separately verified. The journal-writer precondition
fences a change of consent between capture checks and durable append.

Historical availability does not resume a consumed lease or resurrect an expired
expression/selection/send permit. Nothing connects this module to an automatically
enabled production gateway, schedules it, or calls a model/provider/transport.

## Deletion dependencies and storage ownership

Deletion dependencies include the original executable, frame, expression and the
content references carried by selected-candidate evidence. Action and profile
context vaults have separate fixed aliases, not model-proposed filesystem paths.
Context storage comes from the existing MemoryProjection default or explicit
context_vault injection; custom installations must inject the correct context
vault consistently into history and feedback. Unknown storage scope fails closed.

Automatic expiry may remove executable copies while independently consented history
remains. Explicit/ambiguous legacy erasure of a recorded dependency invalidates the
history and verification erases its archived ciphertext and affected managed backups.
The test includes a separate custom context vault, not just same-directory deletion.
Subject-wide erasure also applies through the archive's normal content vault.

This does NOT prove immediate cascade from every erasure command: dependency
verification is currently lazy, and no maintenance/reverse-dependency subscriber
is connected. Cross-device/Halo/external references and maliciously edited ledger/
clock metadata remain unqualified. Do not call a failed read complete forgetting;
qualified live maintenance must erase all derivative copies and backups proactively.

## Actual feedback composition, not an unused archive

FeedbackSynthesizer now prefers the canonical history for a proven delivery. It
does not guess a recent message or reconstruct expired text. If no history exists,
the existing short-lived contract path remains; inbound-only consent creates no
outbound archive. An existing but revoked/erased/unavailable archive causes rejection,
not a fallback that circumvents consent. Multiple eligible histories are ambiguous.
Feedback interpretation retention is capped by both inbound and history lifetimes.
Model interpretation still grants no automatic learning, action or profile authority.

The new synthetic test composes real interpretation/selection/confirmation and
attempt APIs with a fixture signed delivery. After controlled expiry maintenance
physically removes the expression and executable, the archive preserves exact text,
the original expression remains unavailable, and the real feedback snapshot/model-
interpretation API reads that text. Its injected model returns a clarification
interpretation without preference signals; it is not a real model call or user
benefit proof. No terminal delivery evidence is minted from a command success report.

## Verification and limits

Windows history, existing feedback-synthesis and feedback-recovery suites pass.
Seven history scenarios cover repeated capture, scoped access, executable expiry
plus feedback, explicit forgetting, consent revoke, inbound-only rejection, archive
expiry and custom-context forgetting (some checks share scenarios). Deletion tests
use only generated synthetic ciphertext. Controlled cleanup timestamps are not
an actual day-long wait, wall-clock qualification or a real provider/user conversation.

Initial snapshot tree 72fcfd380b74c2ddb7d2134891dd665e0ca1980f, archive SHA256
b0d1ad2b378ed3a6efcf25025c955388c8d26cbef0b66fc63a54a90e47527fdf.
Initial isolated full batch completes 67 suites, but precedes the custom-vault
dependency and interpretation-lifetime strengthening; it does not qualify those
later edits. Final runtime/test tree e39ac14b2d468a8d560f61c2e6d00aa68734dcbf,
archive SHA256 2fc58c792ad4fc1334467d007205467ade64a84a2fe53788791bb879e1e948f0.
Final isolated Linux container alive-delivered-history-full-20261014-r2 is
verified terminal exited 0 with ALL_KERNEL_SUITES_PASSED=67. This includes the
final custom-vault and delayed-feedback composition, lifetime cap, vault/privacy,
authority/outbox, source-review, learning/reflection and actual command-to-local-
sink tests. The broad run remains synthetic internal/command integration evidence,
not real model/user utility, exact provider wire content or production acceptance.

No real model/HTTP calls: totals remain 95 logical / 107 observed HTTP attempts.
No live sends, private chat, production/wmw/other-plugin modification, restart,
credential export or model/channel/auth change. Host receipt/API and exact wire
transformation (including splits/formatting), live capture/maintenance, meaningful
longitudinal learning, layered/external memory, agenda/adaptation, migration/rollback,
portable lifecycle and production acceptance remain required. Signed synthetic
receipts are machinery tests, not evidence that the real Hermes API proves delivery.
