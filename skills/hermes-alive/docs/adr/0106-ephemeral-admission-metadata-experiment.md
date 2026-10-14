# ADR 0106 — Test a bounded metadata handoff through supported native hooks

Status: research implementation and isolated actual SDK experiment;
not registered or consumed by the actual Alive runtime.

## Decision and intended value

ADR-0105 identifies missing bot/quote fields in the admitted snapshot. The live
pre_gateway_dispatch event does carry those fields. Instead of changing Hermes
core or borrowing another plugin's private patch, test a bounded in-process
handoff between these two supported hook sites. Before authorization, remember
only a typed bot bit, quoted message ID and own-message bit, with process-keyed
identity and exact text fingerprints. No plaintext body, quote text, name,
credentials, gateway/session handles or raw sender/chat/profile IDs are stored.
No files, models, authorization, user outcomes or learning are produced.

AdmissionMetadataCache is capped at 256 entries by default, with 30-second
logical lifetime, locked one-time consumption and explicit clear. The matching
identity includes platform, user, chat, thread, profile and incoming message ID.
The admitted snapshot must have the same exact text fingerprint. Missing or
malformed identity returns unavailable. A repeated intake makes its identity
ambiguous rather than selecting latest metadata. Consumed, conflicting and
rewritten identities retain unavailable tombstones until the original deadline;
repetition cannot renew the window. Capacity eviction fails closed for the
evicted entry. Typed bool flags are not inferred from strings/truthy values.

The cache holds raw quoted-message IDs briefly, not quote bodies. Logical TTL
is checked on operations; without another operation, stale bytes may remain
until clear/process teardown. Independent physical timed cleanup and actual
shutdown integration are not implemented or qualified. Do not promise universal
timely forgetting or promote this experiment until those obligations are met.

## Actual experiment, not just a unit cache

A separate test-only native fixture registers both callbacks through the real
Hermes plugin manager. Its pre callback remembers the live event and returns
None; its admitted callback resolves and writes only synthetic metadata into
the disposable test profile. The actual Alive plugin still registers only its
prior observers; it does not use this metadata, and its principal kind remains
unknown. The fixture's class is copied from the tested research module, not an
invented substitute that returns expected flags.

The probe runs actual GatewayRunner admission/auth/pairing methods from ADR-0105.
Denied sources produce no persistent fixture/Alive observations. A synthetic
paired sender resends with a NEW message ID after approval; the authorized
snapshot correctly recovers is_bot=False and its supplied quoted target. A
configured authorized bot recovers is_bot=True even though source.to_dict
omits that bit. Neither classification is feedback usefulness or owner authority.

The fixture also returns a real SDK rewrite directive for one synthetic event.
The actual pre-dispatch method replaces its text. The admitted snapshot cannot
resolve pre-rewrite metadata: the fixture writes null, while Alive continues its
ordinary structural observation. No unrelated target is attached to the rewrite.
The same auth probe without the fixture still passes, so this experiment is not
required by the actual Alive callback. No new learning/outcome event is generated.

Pure cache tests cover conflict, one-time/concurrent consumption, cross-profile
identity mismatch, exact-text rewrite, deadline equality, capacity eviction,
missing IDs, typed flags and clear. Tests use a controlled monotonic clock,
not long sleeps, and pass on Windows and isolated Linux. Their profile test is
NOT a real multiplex route/registry/cache-instance qualification.

## Immutable evidence and remaining work

First snapshot b7e38fd434dc48c2e703af652668c20ae592a3c4, archive SHA256
3aab797023fd101d250629a69ea206880b8a3f000394150bdb79ad162ce2fab9;
alive-metadata-handoff-offline-20261014-r1 exits 0 for cache + actual fixture auth.
Final rewrite-strengthened snapshot 9b654bb284165d43bd9f63df72eefdabd7ad947b,
archive SHA256 ddeccf715a2d128bc3ddcb24de02a5acb340c806a59c9e6f960113fd7f2503ed;
alive-metadata-handoff-offline-20261014-r2 exits 0 for the cache test, actual
auth/metadata/rewrite probe and separate no-fixture auth regression. Containers
use network-none, bounded resources, scratch-only read-only mounts and the pinned
ADR-0103 core/managed interpreter. The auth probe checks DNS/subprocess barriers.
The carrier still warns about missing declared PyYAML/tzdata distributions.

Next qualify real multiplex scope/cache instances, delayed/busy/replayed input,
collision/rewrite ordering, lifecycle cleanup and the host provenance of target
IDs before connecting this to Alive's admitted records. A quoted target is not
a verified delivered history item; ownership/channel mapping and canonical
delivery proof remain required for attribution. An adapter that never populated
quote fields remains unsupported. Do not scrape private chats or treat a visible
quote ID as consent to learn. Current production, wmw, other plugins, README,
public main/version and model/channel/config remain unchanged. No model calls
or real sends; 95 logical / 107 HTTP real-call count is unchanged.

The full goal still requires useful attributed feedback, human-calibrated
semantic decisions, sustained agenda behavior, layered/external memory,
transitive forgetting, portable lifecycle and migration/rollback plus real
production acceptance. This experimental handoff is a prerequisite, not success.
