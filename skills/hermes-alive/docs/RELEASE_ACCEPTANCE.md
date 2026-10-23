# Alive release acceptance and closure

Reviewed: 2026-10-23 (Asia/Shanghai), Codex. Status: NOT QUALIFIED.

This is Alive's product-specific acceptance plan, not a record of passed gates.
Fleet identities, access, directory governance and production windows belong to
the operator's current shared contracts; do not duplicate their changing values
in this public repository. Follow the deployment's current multi-platform test
contract in addition to the requirements here. Neither document grants access,
model-use consent, delivery permission or a production change window.

## Ordered closure

1. Finish a useful installed vertical slice on fresh public material. Show the
   complete original output for owner review. Keep failures, silence, partial
   reading and unsupported interpretations visible. Component tests and model
   self-endorsement cannot establish usefulness or naturalness.
2. Close ordinary installed activation and lifecycle: package-manager dependency
   admission, guided customization, inherited Hermes model/channel capabilities,
   memory permissions, bounded discovery, authorized delivery and feedback.
   Include the share-to-main-conversation continuity gate below: a separately
   generated initiative is not a complete conversational product.
   Shadow preparation is not ordinary live operation. Missing host capabilities
   remain blockers; never patch Core or introduce a second transport queue.
3. Freeze an exact committed candidate. Qualify its regressions and Ubuntu plus
   Windows CI, then test consumer installation from its real remote Git revision.
   No working-directory overlays or manual repairs of the installed files.
4. Execute the platform lifecycle matrix below and state migration/rollback
   drills. Preserve actual command exit status and complete evidence on disk;
   an expired terminal handle is not evidence of success or failure.
5. On that qualified implementation, complete ten consecutive new representative
   full-chain quality rounds. Use fresh materials across technical, domestic,
   broader-interest and out-of-preference cases, including justified silence.
   Do not force content to satisfy a quota or treat soft preferences as gates.
   Each counted round must have an actual useful outcome, complete original
   output and independently inspectable source/decision/transport evidence as
   applicable. A mocked send, prepared draft or accepted request is not delivery.
   Unsigned or absent user feedback is not approval. A failed round resets the
   streak; a material code change requires affected gates and streak to requalify.
   Batched real-send authorization must explicitly bound its destinations and
   scope before execution; this plan itself never authorizes messages.
6. Only after these gates, proceed to release approval, final public-tag consumer
   verification and separately authorized production deployment. Keep code and
   data rollback distinct. Observe real operation and persistence before claiming
   final production completion. Release must not depend on a private Core patch.

Earlier bounded provider/vertical-slice experiments may guide development but
are not retroactively promoted into the final ten-round cohort. Do not endlessly
add judges or memory services in place of closing the useful vertical slice.

## Real platform matrix

| Target | Required real evidence |
|---|---|
| Linux Docker / NAS-like | Fresh disposable container, actual supported Hermes and package manager, runtime UID/group and read-only source constraints, durable volume recreation, installed hooks and actual behavior |
| Native Linux | Actual Hermes installation, Python CLI onboarding, service integration, locking/cancellation and restart persistence |
| Native Windows / Hermes Desktop | Actual Windows Hermes-managed environment, Python CLI throughout without Bash, paths with spaces, locks/process stop, NTFS privacy and installed functional behavior |
| WSL2 | Reuse Linux functional evidence; execute the lifecycle entry points and thin environment smoke for systemd, ext4 versus mounted Windows paths/case/permissions, DNS/network and restart persistence |

For Docker, native Linux and native Windows execute the entire sequence:

`fresh install -> configure -> functional run -> upgrade -> functional run ->
uninstall preserving state -> reinstall -> functional run`.

WSL2 must exercise the real environment but must not duplicate Linux's full
regression merely to inflate test counts. If an environment difference fails,
expand only the affected coverage. An existing reference Gateway, cross-OS
parameter simulation or a Bash-based stub of the Hermes executable cannot prove
fresh consumer installation. Use an existing stable release as the upgrade
baseline, a committed remote candidate for pre-release testing, then verify the
actual published tag before final consumer acceptance. Never manufacture a stable
tag just to make a pending gate appear passed.

## Share-to-main-conversation continuity — required, PENDING

Follow [ADR0210](adr/0210-share-to-main-conversation-continuity.md). Exercise actual
installed Hermes main-agent turns after Alive initiatives; no test-only prompt
overlay may supply context that the installed product would omit.

- A clear ordinary, unquoted follow-up understands the exact preceding share and
  gives a grounded continuation rather than asking what it shared or inventing
  facts. Include both technical material and a nontechnical topic.
- A quotation of an older share selects that share despite intervening messages;
  ambiguous unquoted references ask for clarification rather than choose blindly.
- Inspect the actual main-agent context and source access. Exact outward content,
  supporting material and uncertainty must be available appropriately; do not
  infer correctness merely because a fluent answer resembles an expected one.
- Exercise a delayed physical FIFO drain, failed and uncertain submissions, and
  a crash between submission and continuity persistence. No unsent share becomes
  a seen-message claim, no automatic resend and no duplicated conversation entry.
- Repeat a follow-up after Gateway restart and under normal context compaction;
  respect reset, retention expiry, erasure and revoked authority. Two profiles,
  receiving accounts, users and threads must not contaminate one another.
- Exercise Alive alone and the optional Enhance integration without a competing
  physical queue. No fake user message, unsolicited main-agent turn or unrelated
  task interruption may be used to make the continuity test pass.

Component fixtures are useful negative tests, not this end-to-end proof. Include
conversational follow-up in the final quality cohort as well as source and sending
quality; ten isolated one-way posts cannot establish conversational Alive.

## State and boundaries

- Test synthetic state migration with identity keys, encrypted memories,
  authorizations, configuration, routes, histories, feedback and interrupted
  operations. Verify readable restoration, not just archive existence.
- Preserve account credentials and user configuration. Revoked/expired authority
  must not be revived by import or rollback. Unknown external outcomes must not
  become automatic resends. Historical production messages are never replayed.
- Uninstall preserves owned data; purge needs a separate explicit destructive
  decision. Migration between legacy Alive and the new kernel is unqualified
  until an actual supported transition and recovery path passes.
- Inherit model/auth/fallback and channels from Hermes. A deployment's personal
  interests, model names, recipients, signatures and credentials are not defaults
  for other users and must not enter public fixtures or evidence.
- WeChat Enhance alone owns physical FIFO, token refresh and transport retry.
  Alive owns initiative, memory, selection and outcome interpretation. Validate
  both Alive-alone behavior and the explicitly negotiated Enhance integration.
- Production Gateway/Core, other agents' trees and production data are not test
  fixtures. Restart, real sending and production writes need fresh scoped consent.

## Evidence record

Each gate records candidate commit/tree, Hermes version/revision and dependency
consistency, actual OS/architecture, isolated profile, entry points, terminal exit
status, expected and observed function, sanitized artifact location, failures and
cleanup. Do not publish host credentials, private profiles or message contents.

Use `PASS`, `FAIL`, `PENDING`, `BLOCKED` and `NOT_APPLICABLE` with a reason.
Missing access is BLOCKED/PENDING, never PASS. Do not inherit historical test
results onto a changed tree or claim that a source feature is active in production.

Current kernel quality streak: **0 / 10**. Real four-platform candidate lifecycle,
dual-OS CI qualification and production closure remain pending. Historical tests
remain scoped evidence described in [TESTING_AND_ACCEPTANCE.md](TESTING_AND_ACCEPTANCE.md)
and the [living development plan](ALIVE_KERNEL_PLAN.md).
