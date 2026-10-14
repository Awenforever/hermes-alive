# ADR 0097 — Read deadlines cannot depend on timely erasure maintenance

Status: reproduced expired-content disclosure and corrected read boundary;
delayed-feedback history architecture still required, no production activation.

## Trace lifetime through feedback, not just successful send

FeedbackSynthesizer correctly distinguishes a CLI report from a signed delivered
message and requires complete consented, attributable feedback. It also resolves
the exact executable contract when forming the model snapshot. Natural expression
and its derived executable copy currently have an approximately one-hour lifetime.
That is an execution/intention freshness boundary, not a general long-term memory
policy. After physical expiry erasure, delayed feedback cannot recover that text.
Before maintenance, the vault previously allowed it to be read even past its
retention deadline. Neither accidentally readable expired data nor a permanently
unavailable feedback target is a qualified long-term learning architecture.

The storage issue is verified independently of speculative delayed-feedback
semantics: insert expired synthetic content, resolve it before maintenance. Against
the unchanged vault the focused Windows regression fails because plaintext is
returned. An initial assertion attempt also had a missing exception import; it
was corrected and rerun before claiming the runtime reproduction.

## Read boundary correction

ContentVault.resolve_json now checks the configured retention deadline after scope
checks but before obtaining a decryptor or plaintext. Expired content raises
ContentExpiredError, a ContentUnavailableError subtype. Invalid/naive deadline
metadata is rejected as integrity failure, not an indefinite retention default.
No arbitrary expiry extension, backup resurrection, physical erasure at read time,
preference signal or delivery permission is introduced. Indefinite records remain
unchanged; this does not add consent where none was granted.

The strengthened focused test forbids decryptor acquisition for expired content,
requires the exact expired subtype, then still exercises existing physical erasure
and erased-content rejection. Future/live records, owner boundaries, managed
backups and erasure behavior remain covered by the existing vault suite. Windows
vault and feedback-synthesis suites pass. Full network-disabled kernel replay
results are recorded after authoritative terminal state, not inferred from a few
targeted passes. This broad storage change cannot be qualified only by parsing tests.

The first full Linux batch fails memory.py's expired-history case: the old memory
projector treats ContentUnavailableError as a missing proposal and loses its
structural record. The earlier behavior depended on reading expired content.
Memory projection now treats explicit expiry like erasure for structural replay,
without decoding the value; reads distinguish ContentStatus.EXPIRED with value
None from missing/erased content. Existing validity and availability checks still
exclude it from current retrieval, and expired review activation remains rejected.
The strengthened memory fixture requires the history record AND absence of value,
not merely a weakened no-error expectation. Windows complete memory suite passes.
This preserves event/audit structure, not expired plaintext or a new retention grant.
Corrected isolated Linux container alive-retention-read-full-20261014-r2 is
verified terminal exited 0 with ALL_KERNEL_SUITES_PASSED=66. The full
run_alive_kernel_*.py batch includes the strengthened expiry/decryptor and memory
history tests, feedback synthesis/recovery, learning, privacy/erasure, source
review, authority/outbox and the actual command-to-local-sink composition. Fake
model-call counters inside tests are not new real model calls or product usage.
These tests establish bounded internal contracts, not semantic accuracy, real
host receipts, long-term benefit, installed-device lifecycle or production acceptance.

Deadline checks use stored retention metadata and the host UTC clock. Existing v2
ciphertext AAD does not authenticate retention_until; this fix does not claim to
defeat malicious extension of vault metadata or arbitrary clock rollback. Signed
references and a versioned authenticated-metadata migration require separate audit.
Physical ciphertext/backup erasure still depends on resumable maintenance. A read
denial is not secure deletion or proof that every derivative copy was forgotten.

## Needed separation for the actual goal

Do not solve delayed feedback by extending the executable expression's lifetime.
The intended next architecture separates:

- a short-lived actionable intention, selection and exact send confirmation;
- the historical exact message actually delivered, retained only under explicit
  outbound retention consent and a verifiable delivery/observation provenance;
- inbound feedback with its own consented retention and exact target attribution;
- tentative model interpretation and separately reviewed learning permission.

Historical retention cannot resurrect an expired intent or permit another send.
A CLI success report alone cannot create a claimed-delivered history. Revocation,
erasure and expiry must invalidate downstream artifacts, including archived copies.
The archive must preserve original text rather than synthesize a reconstruction,
and must not silently retain outbound data under inbound-only consent. Whether
real host receipts or explicit quoted-user observation can support this provenance
needs actual host/API integration qualification, not shaped synthetic events alone.
Existing genuine user/host ingress, receipt and feedback-learning gaps remain open.

## Evidence and scope

Initial isolated runtime snapshot tree c4996151f3bba20ff5fed6039597e401a4314242;
archive SHA256 6291a298da078e01b95bb58b3cc6e9bad27528143ed9ff200d35c9d3c427dd0f.
Corrected runtime/test tree 2beced2ad1a40a1613408362eae7216b0d67d330; archive SHA256
61bea67fa5f013c2c465d4714de652aadd581922537a818ac6f8b9dc6f99fb9c.
No live model/HTTP calls: cumulative actual totals remain 95 / 107 HTTP attempts.
All tests use disposable synthetic content. No private chat access, production
deployment/restart/config/model/auth changes, wmw changes or other-plugin edits.
No temporary credential export. Full layered/external memory, sustained agenda,
useful feedback/adaptation, historical provenance, forgetting/migration/rollback,
portable lifecycle and production acceptance requirements are still active.
