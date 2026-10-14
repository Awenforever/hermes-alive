# ADR 0103 — Admit the real SDK surface, not the agent preview as full ingress

Status: native public hook characterized by isolated actual SDK dispatch;
Alive full-ingress capture and actual gateway authorization not yet qualified.

## Source provenance correction

The NAS source export lacks .git, so its directory label alone is not revision
proof. Suspicious-looking _hmwa_* names are also present in official upstream;
they do not establish a local Weixin patch. Preserved local upstream checkout
HEAD is 3f2abce7f468cf194bb7f9ff9c6a033b075d834c with no tracked changes.
Five source files match its NAS-export hashes: gateway/run_turn.py,
gateway/platforms/event.py, hermes_cli/plugins.py, gateway/run_inbound_consumer.py
and hermes_cli/lifecycle.py. This is named-file provenance, not a full import graph,
all exported files, or today's latest revision proof.

A subsequent read-only upstream check on 2026-10-14 finds main at
d97007c32d6340f7ba79ac1dfb5773cc00846448. Fetching into the reference checkout
does not change its checked-out files or production. Git diff from the pinned
revision is empty for gateway/run_inbound_consumer.py, gateway/platforms/event.py
and hermes_cli/plugins.py. Inspecting the new commit's dispatcher still finds
only session_key, platform, source, message_id and text forwarded. Updating
Hermes alone therefore does not provide quoted-target metadata through this
hook at this observed revision. This is source-interface evidence only, not
execution qualification of the new entire runtime or a permanent upstream claim.

Primary sources:
- https://github.com/NousResearch/hermes-agent/blob/3f2abce7f468cf194bb7f9ff9c6a033b075d834c/gateway/run_turn.py
- https://github.com/NousResearch/hermes-agent/blob/3f2abce7f468cf194bb7f9ff9c6a033b075d834c/gateway/run_inbound_consumer.py
- https://github.com/NousResearch/hermes-agent/blob/3f2abce7f468cf194bb7f9ff9c6a033b075d834c/hermes_cli/plugins.py

## Avoid the wrong boundary

agent:start contains a message preview capped at 500 characters, without stable
inbound or quoted-target IDs. agent:end similarly supplies a response preview;
it is emitted before final delivery processing. Neither is proof of complete
input or actually delivered output. The ADR-0013 structural privacy boundary
remains useful; its broader implication of no stable native inbound surface must
not be extended to all public plugin APIs.

The native post_gateway_admission hook supplies session_key, platform, source,
message_id and full event.text. Its documented fire-site follows authorization/
bot admission and several control/busy/slash lanes. It does not necessarily fire
for every inbound message or every intercept. pre_gateway_dispatch precedes
authorization and exposes live handles; it is not an approved replacement for
admitted retention or a license to persist unpaired-user text.

MessageEvent carries quoted-message fields, but the current post-admission
snapshot does not forward them. A stable inbound ID is not the reply target.
Do not guess the latest active message, assume reply_to_is_own_message, interpret
500-character previews as full retained feedback, or silently depend on another
plugin/core patch to obtain quotation metadata.

## Actual SDK characterization

New fixture plugin registers through actual discovery and public register_hook.
The real native dispatch helper and lifecycle/plugin manager invoke it with a
1221-character synthetic event and stable inbound ID. Its source is a plain
synthetic snapshot. The test requires exact text/identity/source fields, confirms
quoted fields are absent, and verifies observer None/error continue ordinary
processing while an explicit handled/reply directive is recognized. No hook or
registry method is patched to manufacture that result.

An initial exact-field-set assertion fails because the real SDK adds
telemetry_schema_version. A diagnostic rerun preserves that discovery. The final
test validates the required fields and additive telemetry rather than pretending
its invented closed field set is authoritative. Those first failed test batches
are not reported green. This does not relax consent/owner/identity checks.

The helper's runner/event/source are synthetic. Calling the helper is not proof
that a real paired message passed gateway authorization, that multiplex profile
routing works, or that a user received/read a message. Only local fixture capture
is performed; a tested audit barrier and Docker network-none prevent external
effects. The production Alive package does not register this observer yet.

## Evidence anchors and next step

Final staged test tree c894c916f61c2d5d410447db8d76183653669ca4; archive SHA256
a4fee40d4bc5f2afa013906f642818f492a69f59a53d7bff8f48e0b0b52876e6.
alive-admitted-inbound-offline-20261014-r3 is verified exited 0, from
2026-10-14T03:25:13.074069953Z to 2026-10-14T03:25:13.828259506Z.
Three actual public SDK callbacks pass, including the deliberately failed
observer/fail-open case. A final barrier-strengthened snapshot has test tree
9769a151d1116285d2644a5c0124bcb0960c30c9, archive SHA256
ae01e19e94cfef9bb5783cd9181d1092513dc298f46ea964b952aa2ec0fca809.
alive-admitted-inbound-offline-20261014-r4 is verified exited 0: actual DNS and
subprocess attempts are rejected by the installed audit hook before the same
three SDK callbacks pass. No live model calls: 95 logical / 107 HTTP unchanged.
No sends/private chat/production/wmw/other-plugin/config/model/channel/auth/restart
change or credential export. README/main/releases/public version remain unchanged.

Next compose consented owner-scoped admitted-event observation with structural
agent topology without duplicate semantics, and obtain/qualify exact feedback
target attribution rather than assume quote support. Real receipt production,
human-calibrated source decisions, longitudinal learning, sustained agenda,
layered/external memory, forgetting, migration/rollback, portable lifecycle and
production acceptance remain open. A working hook is not the full Alive goal.
