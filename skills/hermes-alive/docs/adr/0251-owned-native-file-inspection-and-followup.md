# ADR 0251 — Native decides an owned file inspection and reads its separate outcome

Status: implementation candidate under isolated qualification; not production accepted.
Date: 2026-10-27.

## Authority and purpose

Record review is not a fresh inspection. Add a separate first-guidance choice for
Core read_file-only inspection of exact retained targets from owner-assigned work.
Earlier grants do not expand. The choice includes Core job/model/profile context
and Core-owned task retention; derived decisions/target links use the existing
private vault, bounded to seven days or the item's earlier expiry. It grants no
writes, generic scans, original-work retries, messages or agenda completion.

The current Native owner cycle may decide inspect or wait before communication
cadence is considered. Reuse its model caller and Core scheduler, not a second
agent runner, timer, model router or physical queue. Only one inspection decision
is considered in a cycle. Waits carry a bounded revisit time; repeat inspection
choices reuse the same leaf, including uncertain/failed handoffs.

## Bound evidence and execution

Eligible input is an exact signed producer work, current configuration/policy,
validated live agenda source/version, unchanged authored Core definition and
terminal producer execution. Targets come from actual owned read_file request
pages with matching returned tool-call records. The model chooses an opaque
supplied target ID, never a new path, owner, model, toolset or session.

Create a distinct signed inspection leaf with parent work/execution, item/source
version and encrypted intent. Preserve the normal prepared-paused/bind/recheck/
activate Core handoff and crash uncertainty. The leaf does not replace the
producer in item lookup or become a source for another inspection. Core keeps
the actual request/result; Alive's structural journal keeps references/digests.

Only Core's qualified read-only composition is enabled, with no implicit MCP.
A public pre_tool_call hook additionally checks actual cron identity, owned
binding, unchanged Core definition, current permission/policy/item, and exact
approved read path. It narrows Core access; it does not dispatch a tool or replace
Core permissions. A missing owned authorization blocks the inspection. Hook and
prepared-job disable/unload/purge/recovery still need the full lifecycle matrix;
this is not an OS sandbox or a claim about untrusted operators rewriting Core.

## Decision truth and privacy

Producer records and a separate inspection remain distinct sources. Inspection
readbacks concern the recorded time and may be partial, errors or unavailable;
Core completed is still not semantic success. The separate evidence changes the
existing observation fingerprint and enters the next Native decision. No automatic
repair, retry or completion follows. General autonomous work selection remains
unfinished and is not replaced by this file-specific slice.

Use the existing canonical signed owner-policy verifier for background reads as
well as transport. A materialized enabled flag cannot grant authority when its
signed owner command says paused. Reconfiguration, expiry, erasure or changed
source must stop new use rather than infer authorization from cached rows.

Qualification must execute actual Core producer and inspector jobs, independently
change the artifact between them, reject an unapproved path through the actual
hook, preserve the producer identity, consume fresh observations into a later
Native judgment, suppress repeated work/inference and survive cold reads with the
original keys. Controlled provider decisions prove integration, not real-model
semantic quality, generic task inspection, four-device acceptance or production.
