# ADR 0105 — Real admission gates do not establish human feedback identity

Status: isolated actual Hermes authorization/pairing gates exercised;
full session pipeline, real transport and feedback attribution remain unqualified.

## Why this changes the next action

ADR-0103/0104 called the public admission dispatcher with a synthetic runner;
those tests could not prove that denied messages stayed out of Alive. A new
test uses a bare actual GatewayRunner and its actual _hm_admit_event,
_is_user_authorized_for_source, pre-dispatch hook and bot admission methods.
No authorization method is patched to manufacture a verdict. A disposable
PairingStore generates/approves/revokes a synthetic code, with no external bot,
adapters, credentials, agent startup or private data.

Actual gates reject an unknown group sender; Alive has no journal yet. Actual
pairing approval admits the same sender, after which the real public consumer
dispatcher creates one structural Alive observation and continues processing.
A different sender stays denied. A profile_route_rejected source stays denied.
Actual approval revocation rejects the original sender again without another
Alive observation. These are real gate/code-store executions, not a screenshot
or assertions that an auth-shaped fixture was authorized.

The test composes only the real admission gates and real public dispatcher.
It does not execute the complete _handle_message session/control/busy lanes,
start a service, prove an externally paired user, or validate multiplex routing.
The real native SDK probe remains separate from those higher-level obligations.

## Authorized is not necessarily human or paired

Actual Hermes allows a configured bot source without a pairing grant. In the
same disposable profile, TELEGRAM_ALLOW_BOTS=all admits a synthetic bot. The
real consumer callback observes it, but SessionSource.to_dict omits is_bot;
the snapshot cannot distinguish this author class. This is independent of the
missing quoted-target fields. Neither equality of user pseudonyms nor the
post-admission fire-site is proof of human-originated useful feedback.

Native events now explicitly mark principal_kind=not_exposed_by_host. This
does not manufacture a human/bot decision. Both kinds still carry no learning
or execution authority and do not produce an outcome. Earlier native events
without this marker must be treated as unknown too, never as implicitly human.
The observed newer upstream revision d97007c32d6340f7ba79ac1dfb5773cc00846448
has no diff in gateway/session.py or gateway/run_inbound_consumer.py from the
pinned executed revision 3f2abce7f468cf194bb7f9ff9c6a033b075d834c. This is a
named-file source comparison, not execution of the entire newer runtime.

## Do not route around the boundary with an unsupported slash assumption

Source inspection also finds command hooks precede post_gateway_admission and
their context has platform, user_id, command/raw_command and args/raw_args, not
the stable incoming message ID, chat/thread or bot marker. A new feedback slash
command therefore cannot simply reuse native observation as if both hooks fire
with the same complete identity. Full argument text is useful but is not a
transport identity, attribution target or human authorization receipt.

Next investigate a supported, bounded metadata handoff from the live native
pre-dispatch event to the admitted consumer. Before authorization it must never
persist text/credentials, classify unpaired input as consent, or create learning
evidence. Any experiment must prove matching message/scope, rejected-message
cleanup, concurrency/expiry and rewrite behavior; missing/ambiguous metadata
remains unavailable. Alternatively use an explicit verified target selection
flow, not a latest-message guess. An ephemeral handoff is a proposal to test,
not an implemented or qualified workaround, and does not repair a platform
adapter that never parsed quotation information in the first place.

## Evidence and scope

First gate snapshot 1af4bcbf0ae03a6c816364d61b6d95b5bdd5087a, archive SHA256
159423aae0015fff01af4556fc75a17f541ffa39b6d519c284b85fc65c5dc57b;
alive-host-auth-offline-20261014-r1 exits 0. Extended revocation/bot/route batch
6665d419eade0134242f9cf5740aaaf381c1cb66, archive SHA256
207b92528b488b5e431d06606bfbf045956288218ec8a6ccec4b62161a2315fa also exits 0.
Final snapshot c20ebcc8b28e46c024360b1cd021dd4ea5b06762, archive SHA256
4ddcc95df697b1b45712e72a64d956bab943179c6d629b1fbb9884f35deb920b;
alive-host-auth-offline-20261014-r3 exits 0 after the new auth probe, existing
native-retention regression and actual public SDK capture probe. The final
barrier also actually rejects DNS and subprocess attempts before core imports;
Docker network-none and read-only scratch mounting prevent external effects.
The native retention regression passes on Windows too. This turn does not
rerun or relabel the preceding turn's full 68-script set as new evidence.

The carrier still warns about missing declared PyYAML/tzdata distributions;
installation/dependency qualification is incomplete. No model calls, real
sends, private conversations, production/wmw/other-plugin modifications or
restart; cumulative real calls remain 95 logical / 107 HTTP attempts.
Public main/version/README remain unchanged. Reliable feedback attribution,
human-calibrated learning, sustained agenda utility, layered/external memory,
transitive erasure, portable lifecycle, migration/rollback and production
acceptance remain required by the full Alive goal.
