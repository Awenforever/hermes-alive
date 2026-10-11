# Hermes Alive — Development Memorandum

Internal engineering notes. User-facing README files describe the product;
failure history and non-regression constraints live here.

## Model synthesis must never become Dream again

The semantic need is real, but the old coupling is forbidden. Conversation
interpretation must not combine raw transcript persistence, plugin-owned model
routing and direct memory mutation.

Permanent constraints:

- retention permission and model-learning permission are separate;
- Hermes owns model credentials, primary/fallback routing and channel state;
- only the actual response model is valid attribution;
- evidence text is untrusted prompt data and every citation must refer to the
  bounded evidence window;
- parsing is candidate-local: one malformed candidate does not erase valid
  siblings, and no malformed candidate is repaired with phrase-specific rules;
- model output can create only expiring review proposals, never active memory,
  commitments, actions or user authority;
- raw prompts, raw responses and provider error bodies are not durable data;
- repeated operation IDs cannot repeat the model call;
- no timer or startup hook may invoke synthesis until replay evaluation proves
  usefulness, false-memory rate and review burden are acceptable.

Regression proof lives in
`tests/run_alive_kernel_consolidation_synthesis.py`; the architectural contract
is ADR-0018.

Schema validity is not semantic quality. Consolidation evaluation must use the
complete blinded-review contract in ADR-0019. In particular, do not report
precision without missed durable claims, do not report recall from a hand-entered
aggregate, do not merge sensitive and ordinary unsupported errors, and do not
hide how many review decisions the user would have to make. The synthetic seed
only tests the evaluator; it is never release evidence.

## Event existence is not subject authority

Any kernel projection that cites another event or durable object must prove the
reference belongs to the same subject (or is deliberately subject-neutral).
Never treat a syntactically valid event ID, `USER_EXPLICIT` enum value or real
agenda item as sufficient authorization. Agenda proposals, agenda transitions,
deliberation evidence and deliberation agenda references all require explicit
subject/actor checks. Cross-subject negative tests are mandatory before a new
component joins the cognition cycle.

## Integration must not smuggle in execution authority

The first cognition coordinator ends in deterministic safe silence by design.
Do not add a provider call, sender, tool executor or “temporary fallback” to it.
Future model selection must consume the durable frame through its own reviewed
boundary; future action attempts must recheck current policy and context and
produce their own receipts. A green integrated-cycle test proves persistence
and replay, not permission to act.

The model-selection boundary now exists under ADR-0021. Keep it non-executing:
it may persist a validated intent but must never create an action attempt,
deliver content or run a tool. Rejected candidates must be removed before the
prompt, not merely described as forbidden to the model. Actual response model
identity is mandatory and raw provider failure bodies are never receipts.

Do not collapse selection and execution. ADR-0022 requires a fresh, short-lived
authorization receipt. Direct observation is not user delegation; generic
inbound activity is not confirmation. No sender may treat an expired receipt
as valid, and idempotent lookup must never revive it. Keep `system_critical`
and migrated delegation fail-closed until typed authority provenance exists;
critical gateway notices remain a Hermes-core responsibility.

Never restore a direct `selection -> action.attempted` path. ADR-0023 requires
consumption of an exact live authorization receipt and rechecks latest state.
Recovery order is causal: agenda, frames, exploration, selections, outcomes.
Changing that order can silently turn valid online history into rejected replay.
Do not accept an authorization receipt by field shape alone; verify its local
HMAC and preserve `kernel/identity.key` during managed migration.

Dispatch is an ADR-0024 outbox, not a direct function call. Preserve the
authorization deadline, lease generation and transport idempotency key. Never
persist raw lease tokens or worker IDs. During reconstruction, authenticated
terminal evidence wins over a missing outbox row: restore acknowledged and
reconcile the outcome; never resend.

## Plugin dependencies must respect the Hermes environment lock

The supported Hermes runtime already provides `cryptography==50.0.0`. Alive's
content vault needs AES-GCM, not a newer patch release. Declaring
`cryptography>=50.0.2` caused an isolated plugin install to upgrade the shared
environment against Hermes' exact lock and an MSAL upper bound. Tests still ran,
but the environment was no longer dependency-consistent.

Permanent constraints:

- dependency success means a consistent Hermes environment, not merely an
  importable module after an installer prints a conflict warning;
- pin cryptography to the supported Hermes lock while this plugin targets the
  current Hermes compatibility range;
- change the pin only together with a newer Hermes compatibility declaration
  and a clean-image dependency-resolution test;
- never use an unrelated system Python as evidence for the Hermes plugin
  environment.

## Location onboarding is optional, bounded, and multi-provider

Location/weather personalization must never be an installation prerequisite.
It may improve proactive context only after explicit user confirmation.

Required resolution order for user-entered city/district text:

1. Open-Meteo Geocoding (`geocoding-api.open-meteo.com`), no API key;
2. Nominatim (`nominatim.openstreetmap.org`) as an independent fallback;
3. unresolved user text with weather disabled when both fail.

An explicit `latitude, longitude` pair is an offline escape hatch and must not
perform network I/O. The guided flow must never require coordinates from a
normal user.

The IP-based coarse suggestion may attempt Nominatim reverse geocoding, but a
reverse-lookup failure returns the already available coarse city candidate. It
must not abort or stall the rest of installation.

## 2026-10-02 incident: OpenStreetMap DNS failure

One supported WSL environment could resolve and reach
`geocoding-api.open-meteo.com` but received DNS `SERVFAIL`/interfered answers for
the entire `openstreetmap.org` zone. The old forward geocoder depended solely
on Nominatim, so a normal city correction could fail and the assistant treated
the onboarding flow as blocked.

Root defect: Nominatim was a single point of failure, and isolated provider
availability was confused with overall plugin readiness. Proxy diagnosis does
not solve that product defect.

Permanent constraints:

- do not make a single public geocoder mandatory;
- contain DNS, TLS, timeout, HTTP, JSON, empty-result, and schema failures per
  provider;
- never synthesize coordinates from unresolved text;
- complete onboarding safely with weather disabled when resolution fails;
- preserve the user's text so the location can be corrected later;
- test primary success, fallback success, total network failure, and offline
  coordinate input independently;
- do not add provider API keys or inherit a developer's proxy settings.

## Release proof

`run_location_weather_onboarding.py` must prove:

- Open-Meteo succeeds without touching Nominatim;
- Nominatim succeeds when Open-Meteo fails;
- both providers failing leaves onboarding complete and weather disabled;
- coordinate input performs no network request;
- no public IP or raw lookup payload is persisted;
- existing confirmation, lifecycle, managed-config, and weather-composer
  contracts remain green.

## Query language is not the machine locale

Open-Meteo's `language` parameter selects a localized place-name search index,
not merely the response language. A Chinese place name such as `合肥` returns
no result from the English index even while the provider is healthy. Falling
through from that empty result to an unreachable Nominatim endpoint recreates
the apparent onboarding hang.

The input script therefore takes precedence over a container's often-generic
`C.UTF-8` locale for CJK, Cyrillic, and Arabic place names. A regression test
must prove that Chinese text sent under `C.UTF-8` uses Open-Meteo's `zh` index,
resolves in one request, and never touches Nominatim.
