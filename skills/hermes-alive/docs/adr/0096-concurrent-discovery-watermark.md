# ADR 0096 — Concurrent projection completion is not source loss

Status: deterministically reproduced race; correction under expanded verification.

## Evidence-led cause

The ADR-0095 widened execution regression fails a concurrent delegated-start
scenario with generated candidate evidence no longer current. This is not an
actual user withdrawal or a provider/model failure. A first isolated diagnostic
finds 0 failures in 24 scenarios, which does not disprove the observed failure.
Increasing scheduling interleaving finds 2 failures in 60, and a subsequent
diagnostic captures the inner discovery exception in 3 of 60:
discovery projection could not reach its watermark. Diagnostic containers return
zero after collecting failures; those exit codes are NOT successful test gates.
The explicit failed counts are authoritative evidence of incomplete reliability.

DiscoveryOpportunityIngestor.project_new tests checkpoint < watermark in its loop
condition, then independently rereads checkpoint as the replay cursor. A competing
projector can finish the prefix between those reads. The second cursor equals the
target, replay is correctly empty, but the first reader raises evidence-loss error.
Selection revalidation then rejects a still-valid candidate. Permission checks
fail closed rather than sending improperly, but legitimate execution is interrupted.

The new deterministic test schedules a separate thread to finish projection after
the first checkpoint read, before the first reader continues. Against unchanged
runtime the Windows test fails with the same discovery watermark exception. After
the correction it passes. This is a bounded controlled interleaving, not an inferred
cause based only on successful reruns or a delay masking the bug.

## General correction, unchanged integrity policy

Read one checkpoint per loop iteration and use that same value both to determine
completion and to choose the replay cursor. A checkpoint already at/above the
captured target ends the projection. A competing update during the write phase
still hits the existing BEGIN IMMEDIATE/compare/rollback fence and is reconsidered
by the loop, without lowering the checkpoint or replaying external actions.
This changes no source/profile validation, cryptographic binding, agenda state,
permission or model review. It adds no cached success, arbitrary sleep or relaxed
error acceptance. If an unapplied prefix really cannot be replayed, the test still
requires the error and unchanged lower checkpoint. Restoring replay then completes
the prefix normally; source evidence remains resolvable and projection valid.

Windows deterministic-race and discovery-opportunity suites pass. The exact same
pre-fix authority/lease fixtures and real command-chain scenarios are retained;
do not replace the concurrent failure with a looser expected-error assertion.
Post-fix Linux container alive-host-expression-regression-20261014-r4 is verified
terminal exited 0. Its log passes discovery_projection_race, discovery_opportunities,
expression_support, opportunity_execution, host_capabilities, cli_execution_bridge
and the four-mode actual command-chain suite. The appended original diagnostic,
with increased interleaving and unchanged synthetic authority/budget assertions,
explicitly reports failed 0 / total 60. The zero failed count, not merely its exit
code, proves this bounded stress result. This is not real user/provider delivery
or ten zero-error live Alive calls; it does not establish arbitrary concurrency
or production reliability. Earlier 2/60 and 3/60 results remain failures.

## Anchors and full scope

Corrected staged tree a453aeb8cff36ac026a2ddedb2fe74ff13181b66; archive SHA256
2e6b5e30148b408dc7b01c0025abc62f122e795b97ca58a38bea02937bf1b1bd.
Private pre-fix diagnostics use the immutable ADR-0095 r3 source snapshot. They
instrument exceptions only; no semantic recovery, authorization or retry behavior
was changed. No real model/HTTP calls, sends, private chats, production/wmw/other-
plugin changes or credential export. Cumulative actual calls remain 95 / 107 HTTP.

The useful confirmed-command composition advances integration, not the full goal's
completion. Source judgment, genuine user/host authorization and trusted external
outcome receipts remain unqualified. Layered/external memory, sustained agenda,
useful feedback/adaptation, forgetting, migration/rollback, current portable
installation/upgrade lifecycle and production acceptance remain required.
