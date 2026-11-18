# ADR 0291 — Remove Windows trees without a global long-path setting

Audience: maintainers and QA. Purpose: preserve lifecycle cleanup on native Windows.

The native public-Git consumer completed its upgrade and preserved twelve
existing state fingerprints. Its installed Core control and three Native-wait
cases reached their success markers. The process then failed while removing a
deep temporary backup tree. The host had LongPathsEnabled disabled. A separate
297-character synthetic path reproduced ordinary removal failure; the extended
Windows path spelling removed the same owned tree successfully.

Runtime replacement, rollback cleanup, backup pruning, uninstall and purge now
use a small filesystem helper for recursive removal. It passes an absolute
extended drive/UNC path to the existing shutil operation on Windows, and an
ordinary absolute path elsewhere. Target selection, symlink refusal, permission
errors, file-in-use errors and each caller's existing error policy are unchanged.
No system setting is changed. Source copying and persistent path identities keep
their current contracts.

The deep installed-Core test also uses this path spelling after closing its
owned state handles. Its original failed terminal remains evidence; success
markers before a cleanup failure are not a passing whole run. The filesystem
control passes on native Windows without a system setting change. Full lifecycle
and installed-Core reruns, including their cleanup, remain required.
