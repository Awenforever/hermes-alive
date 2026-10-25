# ADR0227 — Test layout must work with the real public installer

Date: 2026-10-25 (Asia/Shanghai).
Status: layout-only scanner experiment qualified; consumer install in progress.

The actual supported Core public Git installer refused the candidate before
dependency installation: four critical findings among67 came from deliberate
hostile-input and fake-key tests. Core plugin-guard-v11 recognizes root test
directories and any-depth __tests__, but not a nested plain tests directory.
Direct plugin loading and component tests never exercised this public admission.

Use skills/hermes-alive/__tests__ and update executable test entry points. Keep
every negative fixture and its hostile bytes readable. This is the scanner's
documented test-data classification, not an exclusion, encoding trick or local
Core patch. A byte-identical layout-only experiment changed dangerous to caution
with no critical finding and no file omitted. Historical ADR references retain
their original paths; this decision records their current directory mapping.

Retain scan-on-install and Core's refusal of dangerous runtime content. Qualify
the actual scanner with the complete repository and a runtime canary that must
still produce dangerous. Caution is not automatic trust: inspect findings and
use Core's explicit approval path during installation. Do not teach users to
disable scanning, silently accept warnings or claim a forced dangerous install.

Re-run path-sensitive test/fixture entry points and install a pinned public Git
commit into a fresh profile with Core-managed dependencies. The frozen failed
public install and launcher failure remain evidence. Passing this admission is
not runtime, ten-round quality, fleet or production acceptance.
