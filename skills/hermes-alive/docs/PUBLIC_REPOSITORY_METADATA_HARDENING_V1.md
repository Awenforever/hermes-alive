# Public repository metadata hardening V1

Marker: `HERMES_ALIVE_PUBLIC_REPOSITORY_METADATA_HARDENING_V1`

This release candidate adds a root MIT license, least-privilege GitHub Actions
permissions, job timeouts, a fixed PyYAML version, and public security,
contribution, and changelog files. It also removes the two whitespace issues
reported by `git diff --cached --check`.

No behavior is intentionally changed. Because one Python source file receives
an end-of-file formatting correction, matrix and full-scale stress suites are
rerun before the candidate is accepted.
