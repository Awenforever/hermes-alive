# ADR 0108 — Resolve routed identity rather than pre-pin it in the probe

Status: actual canonical routing, scoped auth and metadata handoff tested with a
registered fixture receiver; no external adapter login or full session proof.

## Replace a qualification shortcut

ADR-0107 assigns a synthetic RoutingIdentity directly to a source. The expanded
probe starts with no identity and no runtime profile. A fixture receiver is
registered in the actual runner's secondary adapter map. Actual canonical_identity
resolves transport ownership from that registration, matches a configured
ProfileRoute against platform/chat/receiving-bot profile, checks the actual served
profile directory set, resolves the target home and pins the identity itself.
Assertions require the correct live weakref to the fixture receiver, distinct
authorization/runtime homes, non-inferred transport and stamped source.profile.
No identity/resolver/auth function is mocked or patched to pass.

The fixture is not a network adapter: source construction and registration remain
synthetic. This tests the real selector/resolver code with controlled inputs,
not transport credential validity, an externally received message, startup
adapter wiring or the full _handle_message/session/busy/control pipeline.

## Bootstrap is part of the contract

The first attempt constructs GatewayConfig(multiplex_profiles=True) but does not
publish the actual process multiplex mode. Its auth assertion fails: scoped
gate readers only consult profile secrets when that bootstrap mode is active.
Config truthiness and a profile scope alone are not a running gateway.

The probe now calls the real set_multiplex_active(True) in its disposable process
before scoped gate reads, as the gateway bootstrap does. It neither monkeypatches
the auth result nor writes the grant into ambient os.environ to mask isolation.
This test setup correction must not be mistaken for an Alive runtime fix: Alive
does not own/publish the gateway's process mode.

## Separate who authorizes from where the agent runs

The two disposable profiles deliberately allow different synthetic users in
their .env. Actual _hm_admit_event and _is_user_authorized_for_source admit the
receiving transport's allowed sender. The real pre/post SDK handlers deliver its
task-bound quote metadata only in the routed runtime home, using different actual
plugin managers. A sender allowed only by the destination profile is denied by
the transport's policy; no admitted metadata observation is appended for it.

A second configured route points to a nonexistent/unserved profile. The actual
canonicalizer refuses it, stamps profile_route_rejected and the actual ingress
gate rejects it before plugin intake. It does not fall back to a default agent,
create that profile directory or append another destination observation.

## Evidence anchors

Initial snapshot 61dc7838f2cffb071145cbcd83067234949e05b6, archive SHA256
19a078c9a9025db08409cff2d51c065aa85c4463e4794a7fdf244b495a99f15d;
alive-metadata-canonical-offline-20261014-r1 exits 1 on auth (missing bootstrap).
Corrected snapshot 39ea4658263d389c7222c9ac984bad41dd6a4004, archive SHA256
7799db47c96a4dcf9cb516cc1f11155a5989c02e686c77e8ae317d1c893c1905;
alive-metadata-canonical-offline-20261014-r2 exits 0. Final unserved-route snapshot
2e2774831b230de9e7875ccc7ef36066d63d9744, archive SHA256
58f1fb219cd7f8fb0dfdd2f597396536e65201eb0bb8218aa87c112badb2d608;
alive-metadata-canonical-offline-20261014-r3 exits 0 after canonical/auth/task
handoff, the prior pinned-identity scoped probe, task-cleanup and cache regressions.
The first failed batch is preserved, not relabeled green.

The immutable containers use network-none, bounded resources, scratch-only
read-only mounting and the pinned ADR-0103 core. No model calls, real messages,
private conversations, production/wmw/other-plugin/restart or model/channel/config
change. Real totals remain 95 logical / 107 HTTP attempts. Actual Alive registration,
public main/version/README remain unchanged. This turn changes test qualification
and living documentation, not production behavior.

## Remaining critical path

Run the full gateway session/control/busy/task path and lifecycle failure cases
before connecting the research handoff to actual Alive observation. Match target
IDs to owner/channel-scoped canonical delivery receipts and exact history, not
simply a quote or a CLI success report. Grant/erasure boundaries must survive
attribution and subsequent model waits. Useful learned agenda and sustained
proactive value, calibrated semantics, layered/external memory, transitive
forgetting, portable installation/upgrades and rollback plus actual production
acceptance remain the unchanged full objective.
