# ADR 0104 — Observe complete admitted input without manufacturing feedback

Status: development implementation; real isolated SDK dispatch qualified for
synthetic capture, not actual gateway authorization or production rollout.

## Decision

Register post_gateway_admission through the native Alive plugin, separately from
legacy agent hooks. The callback always returns None, including capture failures.
It is off unless HERMES_ALIVE_KERNEL_SHADOW_ENABLED is explicitly enabled. No
normal reply, slash command, queue or model route is consumed/modified. Gateway
authorization remains Hermes' responsibility; an internal function call or a
payload-shaped source is not independently proof of admission.

Native events are conversation.admitted, not another conversation.inbound agent
turn. They have stable, installation-keyed identity over platform, user, chat,
thread, session and inbound message ID; raw identifiers are not journaled. Exact
text fingerprinting preserves whitespace and rejects identity reuse with changed
text. Distinct native/agent evidence roles do not automatically become two
feedback observations. No attempt causation, quoted-target assumption, delivery,
learning grant or outcome is invented. This boundary must later feed explicit
verified attribution, not a latest-message heuristic.

Default capture is structural only. Existing /memory consent uses the same local
user pseudonym and routed profile storage. Native retention checks the latest
canonical self-issued consent, including direction, lifetime and sensitivity,
rather than a potentially stale projection. Authorized text is encrypted using
the existing erasable vault with an explicit complete-native contract; whitespace
and text beyond 500 characters are preserved. A one-million-character storage
limit rejects rather than silently truncating. Later model feedback limits are
separate; large retained input is not automatically a safe prompt.

Consent generation is rechecked inside the journal writer transaction. Revocation
between encryption and append aborts publication and removes the uniquely owned
orphan copy. Concurrent duplicate capture has separate temporary content IDs;
only the winning event's copy remains. Replay returns the original receipt,
never renews expiry, backfills content after consent, or recreates forgotten text.
Malformed identities are rejected before creating state. Failure logs contain
exception classes only, not user content, source identifiers or exception text.

## Real runtime failure and correction

The first actual SDK batch loads the real Alive plugin but cannot record its
native event: the existing embedded loader executes the kernel's convenience
facade, which imports recovery and installed-hook-only safe_io. Local tests have
the hooks directory on sys.path, hiding the defect. The observer's isolated
namespace now loads only its module and relative dependencies, without executing
the facade or modifying global paths. This also fixes the existing tool observer
loader. The convenience public kernel package remains unchanged.

## Evidence

First failing immutable source tree 571a316f3dd1a38fe88193da11951251ab1e25df,
archive SHA256 3e81bc928f46fa25096e4806e7c914a410c4e124ac6eb6ca0960f827c1619c2c;
alive-native-observer-offline-20261014-r1 exits 1. Do not count this as green.

Corrected source tree fede8d41f2d68ee85872462f29e02498aca47b7a,
archive SHA256 2d4f3f3a20a096916b51e4a4f7d6fb9aa28477d990c81a83c3fac44ffd3c5351;
alive-native-observer-offline-20261014-r2 exits 0. Real native discovery/dispatch
loads the actual modified Alive plugin alongside the test fixture. Off-state
creates no journal; shadow-on captures one structural input, then canonical
consent authorizes exact encrypted retention of the second 1221-character input.
Both return ordinary-agent continuation. No outcome is written. The SDK failure
fixture still fails open. Network-none and tested DNS/subprocess audit barriers
prevent external effects. Core revision is the pinned ADR-0103 runtime, not a
claim that the entire new upstream main was executed.

Final code/test snapshot 53d9b5ceb4367cd0c5a4995bb28f68a088f919aa, archive SHA256
c26f23ef185fb4360023886bd821f1bad5902143c107c7c830ba3edabe1a835f adds the
forced simultaneous-copy regression and writer-time lifetime check. The
alive-native-observer-offline-20261014-r3 container exits 0 after native-input,
tool-receipt and retention regressions plus the actual SDK probe. This is the
final isolated runtime evidence, without silently reclassifying the failed batch.

Local regressions additionally cover exact whitespace, missing owner, no consent,
outbound-only/revoked consent, another owner, conflicting stable IDs, replay after
erasure, revocation during put/append and simultaneous two-copy capture. The
concurrency test forces both encryptions to finish before either append to avoid
a misleading merely sequential pass.

The broad Windows runner initially stops after 34 successful scripts because
the host-expression script requires --hermes-root. This is a failed harness
invocation, not a green complete batch. Resume runs only the 33 remaining scripts:
32 pass and the official-hook test explicitly skips without a local Hermes
runtime. Both runtime-dependent scripts are then actually executed, not skipped,
in isolated Linux containers with the pinned core: four host-expression transport
modes pass, and the official HookRegistry/plugin-manager contract passes.
The latter fixture's explicit distribution copy list is updated for the new
bridge module. In total 66 Windows tests and two actual Linux host tests cover
the 68-script set; this is not whole cross-platform installation qualification.
Official-hook snapshot 9eec6241720d74dfb47783ff6f497fd79a047837, archive SHA256
e0e4b4a1986852801709a1580f1729f9663cd849989b2ffd6c7b860fa03fb8ef;
alive-native-observer-official-hooks-20261014-r4 exits 0. The separate host chain
uses r3 and alive-native-observer-host-chain-20261014-r3 also exits 0.

The isolated carrier still warns that declared PyYAML/tzdata distributions are
missing; successful observer execution is not complete dependency installation
qualification. Real pair/auth gates, multiplex routing, non-user bot semantics,
quotation transport, actual incoming traffic, installed lifecycle and latency
qualification remain open. All channels/providers/consents here are synthetic.
This turn makes no model calls, sends, private reads, production/wmw deployment,
restart or configuration change. Public main/version/README remain unchanged.

## Next work and full-goal alignment

Qualify profile/owner admission and user/bot distinctions against the actual
gateway path. Obtain reliable quoted-target metadata or an explicit user-selected
target through a Hermes-owned supported interface; do not patch another plugin
or silently assign the most recent action. Bind exact native input to confirmed
delivered history before semantic feedback, then assess whether learning improves
sustained agenda and useful proactive expression. Layered/external memory,
longitudinal utility, transitive forgetting, portable upgrade/rollback and real
production acceptance remain required; a working ingress observer is not Alive.
