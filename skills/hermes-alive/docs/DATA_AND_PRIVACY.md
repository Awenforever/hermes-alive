# Data and Privacy

## Local data categories

Hermes Alive may persist:

- managed non-secret configuration;
- bounded conversation and activity context;
- voice and interest profiles;
- proactive delivery and decision logs;
- Discovery cache and content evidence;
- topic reservation and delivery history;
- encrypted, expiring typed-memory proposals and review state when separately
  authorized (legacy Dream transcript processing is retired);
- Circadian sleep/wake state plus shadow/live enforcement observability;
- an optional confirmed location profile.

The lifecycle default shared root is:

```text
$HERMES_HOME/plugin-data/hermes-alive/runtime
```

Runtime components honor `HERMES_ALIVE_SHARED_DIR` when a lifecycle-safe path is
explicitly supplied.

## Data minimization

- Provider credentials remain in Hermes configuration.
- Raw user messages are not persisted in Circadian intent or quality-governor
  state.
- Topic-delivery history stores hashes, timestamps, reasons, and update
  fingerprints rather than raw URLs or titles.
- Quality observability stores hashes, classifications, bounded counters,
  timestamps, and opaque episode identifiers.
- Rejected candidate bodies are not written to enforcement observability.
- Successfully delivered Alive outbound text is retained in the rotated local
  proactive log so an owner can audit what was actually shown. Unsent drafts
  and inbound user messages are excluded from this delivery record; the file
  is owner-only (`0600`).
- Logs and JSONL files are bounded or rotated.
- Interest learning does not infer sensitive identity traits.
- Fresh installs retain no conversation body and perform no model memory
  consolidation. Content retention and model learning require two separate,
  per-user Hermes-authorized choices.
- Consent-gated memory synthesis reads only live decryptable retained excerpts.
  Its prompt and raw response exist only for the model call and are never
  written to the journal, logs or receipts. Receipts retain evidence IDs,
  actual-model attribution, bounded counts and error classes; accepted parser
  output enters only the encrypted review-proposal path.
- The checked-in consolidation replay seed is synthetic and manually marked as
  privacy reviewed. Historical conversation excerpts must not be committed as
  a test corpus through automatic redaction alone; any future historical corpus
  requires an explicit human privacy review and a separately controlled
  storage decision.
- Model deliberation sends only candidates already admitted by deterministic
  policy and the exploration gate through Hermes' configured model route.
  Prompts and raw responses are not journaled. Candidate bodies and rationale
  remain encrypted; structural receipts retain actual-model and selected-ID
  provenance without provider error text.
- Send-time authorization stores structural IDs, policy values, reason classes
  and permit expiry only. Candidate and agenda bodies remain in the encrypted
  vault. A receipt expires rather than extending authority on retry.
- Action attempts retain the structural authorization event ID, capability and
  idempotency key, never the candidate body or transport payload.
- Authorization receipts are authenticated with the installation-local
  identity key. The key is never journaled and must travel inside the managed,
  access-controlled kernel backup boundary.
- Dispatch rows contain content references, pseudonymous lease owners and
  keyed token digests only. Raw worker identities, lease tokens and candidate
  plaintext are never persisted. Terminal result events are locally
  authenticated structural facts without transport payloads.
- Dispatch-start events contain structural IDs, policy identity, capability,
  idempotency identity and lease generation only. The execution grant holds
  plaintext in process memory; neither start nor uncertain state journals it.
- Action permits persist an installation-keyed authenticator and schema
  version, never message text or raw routing. The encrypted action document
  contains no destination; route identity must come from separately authorized
  Hermes configuration.
- Autonomy policy stores only structural risk/interruption bounds, its revision
  and user authority. Raw control commands are forbidden. Policy events carry
  an installation authenticator and contain no channel identifier or message
  content.

## Topic-delivery privacy

Canonical URL and semantic topic identities are converted to stable hashes before
persistent storage. Reservation, delivery, release, expiry, and material-update
state use those hashes. Corrupt primary history recovers from a valid backup;
unreadable primary and backup state fails closed instead of admitting duplicates.

## Location onboarding

Location is optional. The terminal does not ask for coordinates or a place name.

When the installer explicitly allows network-assisted lookup, the network exit IP
may be sent to the selected coarse-location service. The result remains
unconfirmed and weather stays disabled. Hermes may ask one natural-language
question in the existing chat. Manual correction/geocoding sends only the typed
place. Weather requests send only the minimum confirmed region or coordinate
data required by the service.

The system does not send Hermes chat content, user identity, session data, model
credentials, or Provider secrets to location/weather services. Raw public IP and
raw lookup responses are not persisted.

A confirmed profile may store:

- enabled/confirmed/onboarding-complete flags;
- display name and administrative levels;
- latitude/longitude;
- timezone;
- source class and precision.

A changed network exit never silently replaces a confirmed profile. There are no
fallback coordinates.

## Removal

Default uninstall preserves shared user/runtime state. `purge` removes all Hermes
Alive-owned shared state and is destructive.
