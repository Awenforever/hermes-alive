# ADR 0243 — Observe real Core work without inventing its outcome

Status: implemented; isolated Core qualification, not production acceptance.
Date: 2026-10-26.

## Gap and decision

Installed execution still grants only share/ask. The existing structural tool
observer was gated by the experimental shadow environment and did not attribute
observations to the configured owner. That is insufficient experience for an
ongoing assistant; it must not be advertised as working outcome learning.

Add an independent default-off guided choice to observe the configured owner's
Core tool names, durations and terminal classifications. Preserve no arguments,
result bodies, error bodies or raw session/task/call IDs. Reuse protected setup
storage and keys; do not initialize storage from a hook. The current Core
SessionStore/route, task-local identity and signed configuration bind ownership.
Foreign, cron/unbound and stale configuration contexts cannot borrow this grant.
Recheck permission at journal append. Duplicate call coordinates deduplicate the
observation, not the tool invocation. Unload closes observation with its binding.

The structured journal remains until explicitly removed. Events have a diagnostic
validity deadline from the selected retention period; expiry is not a claim of
physical deletion of an immutable ledger. Disclose both lifetimes. Reconfiguration
without the observation choice stops new observation. This does not enable model
calls, proactive contact, private transcript collection or tool execution.

Core's ordinary ok/error labels are classifications of tool returns, not
independent success evidence. Keep their outcome unknown. Executor-backed block,
cancel, timeout and exception can establish those terminal facts, not a new
preference or permission. No automatic semantic learning is enabled by this flag.

## Qualification and next boundary

An actual installed Core profile invokes native write_file/read_file through
model_tools.handle_function_call, including its native observer hooks. Independent
OS reads verify the synthetic artifact; the journal still says success unproven.
Native pre_tool_call veto prevents a later write, whose blocked receipt is
attributed separately. Default opt-out and mismatched session envelopes produce
no receipts. These are synthetic profile/tool operations without model, network,
channel sends or production access. They do not establish Alive-selected work,
generalized semantic outcome verification, reflection/adaptation or distribution.

For future side effects, do not reuse PluginContext.dispatch_tool as a complete
approval executor: supported Core source shows it forwards directly to the registry,
whereas model_tools.handle_function_call owns pre-tool guards/middleware and the
post-tool envelope used here. The public subagent lifecycle also requires an active
parent and cannot reconnect after process exit. Neither is evidence for a durable
unattended worker. Continue through Core-owned execution/approval capabilities;
do not create an alternative shell executor or silently expand contact grants.

The owner's current product choice is first-guidance selection of automatically
allowed action scope, with per-operation confirmation outside that scope.
Accepting ongoing work is not itself that execution grant. This choice is recorded
here and in the living plan; actual action permissions remain unimplemented.
