# ADR 0100 — History erasure must not depend on a later content read

Status: metadata-only maintenance connected to local retention/startup recovery;
no production deploy, qualified periodic service or general forgetting completion.

## Connected erasure path

ADR-0099 invalidated and erased a history derivative when its reader checked
explicitly forgotten dependencies. That lazy path is insufficient when nobody
reads the record again. DeliveredHistoryStore.reconcile_erasure now scans all
relevant history events, optionally owner-scoped, without a latest-N cutoff.
It authenticates history payload, canonical identity and structural ownership,
and compares the signed content reference with the target vault row before any
deletion. It does not decrypt historical text, reinterpret it or recreate copies.
Unverifiable records/storage scopes are counted as unresolved, never guessed.

An explicit dependency tombstone triggers normal scoped archive erasure and
affected-backup purge. Automatic expiry of an executable alone does not destroy
independently consented history. Already absent copies are not reconstructed;
pending physical erasure/backup completion remains the vault's responsibility.
Repeated sweep is idempotent. Its authorization is the signed dependency linkage
and existing explicit deletion, not a model hypothesis or current send permission.

Existing resume_retention_maintenance now sweeps history after erasure resumption,
memory projection and expiry cleanup. KernelRecoverySupervisor does the same in
startup recovery after dependency-ordered replay/outbox reconciliation. Their
reports include erased and unresolved derivative counts; the startup handler logs
these and emits an error when unresolved dependencies require operator attention.
Legacy watcher availability is not redefined as successful privacy recovery.

## Tests and evidence boundaries

Expanded synthetic history tests deny decryptor acquisition during a metadata
sweep, verify erasure without reading history, affected-backup removal, repeat
convergence, separate-context-vault erasure, and preservation across ordinary
executable expiry. Additional runtime-layout fixtures execute the actual local
retention-maintenance and startup-recovery APIs, requiring an erased derivative
on first recovery and no duplicate erasure on second recovery. Their default
shared vault layout is explicit; it is not a guessed custom storage migration.

A forged history payload pointing at another owner's content must yield an
unresolved count without deleting that content. Integrity errors are not silently
green reports. Synthetic model counters and fixture receipt signatures do not
qualify genuine gateway ingress, provider delivery or user benefit.
Focused Windows history, recovery and retention suites pass before the final
forgery fixture is added; final broad Linux results cover the complete snapshot
and are recorded only after authoritative terminal verification. Final isolated
Linux container alive-history-maintenance-full-20261014-r1 is verified exited 0,
with ALL_KERNEL_SUITES_PASSED=67. It covers the complete final snapshot, including
the forged-maintenance fixture and actual retention/startup API composition.
The official-hook contract test also emits a carrier dependency warning for
PyYAML/tzdata; this source-level batch is not a qualified PM installation or a
claim that all plugin runtime dependencies are installed. No installed-device,
provider/user conversation or production acceptance is inferred from these tests.

## Still required

The sweep is connected to startup and an existing maintenance API, not yet to a
qualified periodic/privacy-command subscriber in every supported environment.
Long-running gateways, custom/external/Halo storage, crash/race windows between
new copies and erasure, transitive model-derived artifacts, lost/corrupted vaults,
large-history cost and backup replicas require further qualification. Unknown
scope reporting is not deletion completion. Nor does this authenticate a maliciously
edited erasure ledger or ensure erasure when the plugin/service is not running.

Real host history capture/receipt production, paired feedback attribution, useful
longitudinal learning, layered/external memory, sustained agenda/adaptation,
migration/rollback, Windows/Linux/WSL/Docker lifecycle and production acceptance
remain open. No reduced scope or final completion is claimed from this sweep.

## Immutable anchors and safety

Final runtime/test tree 8f66feef3648982b1569d2910bf0e0eb4a1721f3, archive SHA256
40db1bb4f545e751636232951e7057ca3876019ddbe0bf52777ec9f2f7bfa7f3.
No real model/HTTP calls; cumulative totals remain 95 logical / 107 HTTP attempts.
Erasure touches only generated synthetic test content. No production data/config/
model/channel/auth or restart change, no wmw/other-plugin change, private chat or
credential export. Public version/main/releases/README are unchanged.
