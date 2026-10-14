# ADR 0112 — Recoverable discovery-to-intent runtime

Date: 2026-10-14

## Decision

Add `alive_kernel.planning_runtime.PlanningRuntime` as the runtime composition
of retained discovery interpretation and cognition selection. The host supplies
a current policy, model-call capability, sensitivity and authority explicitly on
every entry. It inherits model routing through that capability; no provider names,
credentials, private interests or channel destinations are public defaults.

The wrapper is a planning part of the autonomous loop, not a separate queue,
delivery adapter, replacement watcher or complete production loop. The next
steps must connect expression and current action authorization, then delivery
evidence and user feedback, before production acceptance is meaningful.

## Recovery contract

- A stable owner/operation namespace links interpretation and selection. Canonical
  structural start records bind the current host policy/model/authority contract;
  reusing an operation under a different contract is rejected before provider IO.
- Input identities, literal interruption permission and requested model shape are
  checked before creating a durable planning record.
- Retained completed interpretation is resolved through its real evidence checks.
  Started but incomplete/failed interpretation is not silently repeated.
- Selection has a deterministic identity. A completed current selection is
  recovered without another provider call. Started but incomplete selection is
  not silently repeated either. Underlying exclusive operation starts still
  protect provider spending; the wrapper does not invent weaker retry semantics.
- Interpretation is revalidated after selection's await, so withdrawals cannot
  be hidden behind a successful selector response. A superseded selection cannot
  be returned as the current runtime intent.
- Re-entry does not restore authority from a model or a draft: the host must
  supply the same explicit input contract. This still is not a dispatch grant.
- Protected interruption windows and model abstentions retain an actual silence
  selection. Provider cancellation is not reported as successful silence.

## Evidence and limits

Windows and isolated Linux tests pass for a sharing proposal, protected window,
abstention, cancellation during interpretation, cancellation during selection,
provider-free completed recovery, changed-policy refusal and malformed-host input
rejection before journaling. Cross-cycle ADR-0111 regression also passes on Linux.
Model responses are controlled synthetic fixtures, not real-model quality proof.
The actual legacy watcher does not yet invoke this runtime; no external transport,
new platform FIFO, production configuration, restart or user message is involved.

Linux container `alive-planning-runtime-offline-20261014-r1` exited 0. Its scratch
mount is read-only; network is disabled, resources bounded to 1 CPU/2 GiB/256 PIDs.
The base is the unchanged ADR-0111 source snapshot plus these two exact files:

- runtime SHA-256: `2bee0552666728973df9c4e9c952f0e37f492a9a70f50cab6be190f4426e88ef`
- test SHA-256: `2f5f7743429fb2b3a9ddda6e13d79c7181415c49aea6fd8858c4c76db7fba0f1`

An initial local runtime failure tried to digest a frozen event mapping directly.
The implementation now thaws that typed payload before finite canonical JSON
digesting; no event/source validation was bypassed to make the test pass.

Open qualification: concurrent runtime entry and shutdown, stale final-expression
recovery, fresh real-model scenarios, scheduler registration/budgets, privacy and
attribution at live ingress, consented durable delivery history, long-running
utility, fresh install/upgrade and rollback. The full Alive goal remains active.
