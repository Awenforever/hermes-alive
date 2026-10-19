# ADR 0189: Configuration-driven Core shadow assembly and engine installation

Date: 2026-10-19
Status: focused actual Core configuration/install/reload proof; final qualification pending

## Remove manual runtime injection

`kernel-setup` requires explicit model-call consent and an explicit owner resolved
from current authorized Hermes metadata. `--user-id` uses the existing installation
pseudonym convention; raw IDs are not stored in settings. Advanced existing subject
IDs remain supported. The configuration contains only shadow consent, owner,
bounded lifetime and an optional Core model choice, never keys or an owner preset.
The installation guide must ask natural questions, not ask users to invent IDs.

Gateway startup now assembles its own journal/vault/policy/native host from these
persisted settings. Missing or disabled settings do nothing. An existing paused
journal policy is never silently re-enabled on restart. Equivalent omitted/default
values normalize consistently; actual consent/model/state changes revoke old work.
The mature source/meaning checks and consent-bounded feedback path are retained.
All execution remains shadow-only; no destination, send capability or transport
queue is granted. Discovery input still needs host-read integration, not fake news.

## Core owns models, secrets and retry/fallback policy

The automatic host uses its real PluginContext LLM facade, not a copied auth store
or a plugin provider registry. The existing NativeCognitionHost loop admits an
explicit current caller factory rather than adding a second scheduler. Core's
owned auxiliary task `hermes_alive_kernel` inherits the active main model and
receives the normalized current main fallback chain from Core's own helper as
runtime defaults. User task configuration wins. No fallback chain is persisted
in plugin settings; no retry classifier or API key reader is implemented here.

The public result drops finish metadata, so a qualified Core ABI bridge follows
the same `_gate -> _invoke_async -> _finish` pipeline, examining the raw SDK
response before it is discarded. Core still gates overrides, resolves auth,
routes and retries. Explicit native SDK model/choice/message/finish fields,
`stop`, no tools, and exact audited/native text are required. Truncated, filtered,
missing or compatibility-synthesized finish markers reject, even if JSON parses.
This uses private Core method ABI: unavailable ABI fails closed and upgrades need
actual integration qualification. Do not present it as a universally supported
public transport API. Other normalized API shapes remain unqualified.

Calls have finite token/time/count bounds, current profile/config/consent checks,
and current-authority checks after await. Configured route overrides cannot widen
the text-only boundary. Pending state exposes metadata, never raw task handles.

## Install, upgrade, uninstall, reinstall

`install-runtime --engine kernel-shadow` selects the dedicated adapter in the
same owned hook slot, with atomic swap/rollback and correct engine-aware hashes.
Default ordinary installs remain legacy while the kernel is experimental.
No-argument upgrades retain the chosen engine. Normal uninstall preserves engine
choice in its tombstone plus configuration, identity keys and journal/vault data;
reinstall restores the chosen engine. Verification reports Core binding as
unverified rather than pretending a configuration check proves live functionality.
Restart still requires explicit operator approval; no production restart occurs.

## Evidence and unresolved release gates

Actual Core548e66f code-copy profiles run the real public plugin setup/install CLI,
disk hook, configuration writer, model SDK and lifecycle uninstall/reinstall.
Controlled HTTP verifies automatic assembly without injected Python runtime objects,
reload without duplicate inference, identical journal bytes across code reinstall,
unconfirmed setup with no config write, stable pseudonymous owner, Core override
denial, invalid finish rejection, in-flight consent revocation and another profile
using the same model/provider labels with different endpoint/key. No network,
actual model intelligence, physical sends or production configuration changes.

Initial experiments incorrectly expected generic403 to switch models. Core's
auxiliary classifier treats401 (and specific bad-credential403) as auth errors,
not ordinary403. Owned task defaults alone do not change that. Preserve those
failed runs; generic403 remains propagated and unqualified. Forwarding Core's
configured chain into its owned task qualifies401 fallback, not every error class.
Do not silently implement private provider hopping to obtain a green test.
An additional held-call fixture initially overwrote explicit `model: null` with
an omitted field, provoking the consent guard; normalize equivalent defaults and
retain the failure instead of relaxing real revocation checks.

Retained environment still warns about missing declared PyYAML/tzdata, so this is
not fresh managed-dependency/platform admission. Source-only tests use fake Core
facades and cannot replace the actual SDK test. Final archive must repeat the
automatic path, prior installed-startup/legacy regressions and full portable CI.
Generic403 semantics, all API modes/renewal, automatic source reads and bounded
error recovery, useful real recommendations, long-term memory/agenda/outcomes,
portable lifecycle/migration, ten fresh complete clean rounds and production
acceptance remain open. No formal release or production activation follows.
