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
- The rebuildable dispatch-evidence projection duplicates only journal
  sequence, event ID/type and attempt ID. It contains no payload, message,
  route, worker, lease token or external recipient and never replaces journal
  integrity/authenticator checks.
- Action permits persist an installation-keyed authenticator and schema
  version, never message text or raw routing. The encrypted action document
  contains no destination; route identity must come from separately authorized
  Hermes configuration.
- Route locators are encrypted in the content vault under their subject and
  purpose. The journal retains only their content reference, keyed fingerprint,
  exact user-authority event, host snapshot and binding authenticator. Route
  erasure or revocation fails closed before dispatch; no raw platform chat ID
  is admitted to the append-only journal.
- Autonomy policy stores only structural risk/interruption bounds, its revision
  and user authority. Raw control commands are forbidden. Policy events carry
  an installation authenticator and contain no channel identifier or message
  content.
- Discovery observation bodies (including title, URL, summary, source and
  author metadata) live only in the encrypted vault. The journal and
  rebuildable entity projection retain installation-keyed entity/version/source
  fingerprints and structural references. A raw chat ID used to scope shadow
  ingestion is pseudonymized before it enters the kernel. Source failures keep
  only keyed source/error-class fingerprints and cannot create opportunities.
- Availability events contain pseudonymous subjects, bounded reason codes,
  stance, evidence basis and expiry only. They contain no message text, raw chat
  identifier, schedule body or Circadian phase. Projection corruption fails to
  `unknown`; inactivity is never persisted as permission to contact the user.

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

### Kernel development: native work request retention

New explicit follow-up intake/management guidance separately discloses retaining
the exact current request (at most 6000 characters) in the existing encrypted
vault for the chosen item lifetime. The signed journal holds its content reference
and keyed fingerprints, not plaintext. Only admitted request/management turns are
retained; this grants no casual-chat collection. Older grants without this source
choice remain descriptions only. Inventory exposes availability; exact item
lookup and authorized cognition may read the retained original as evidence,
distinct from interpreted agenda text. Expiry or erasure makes that source
unavailable; descriptions cannot reconstruct it. Full dependency-erasure and
cross-store migration qualification remain release gates.

Separately guided native background work uses Core's own model/profile context
and task records. New guidance explicitly includes the current owner message
for each handoff, at most 6000 characters, as exact source context alongside the
prior agenda description. Longer requests are refused without truncation. This
does not collect conversation history. Alive retains causal references and keyed
fingerprints, not another copy of that message. Core task-record retention is
separate from Alive's item/outbound retention; removing only Alive cannot erase
Core's records. Old grants without the source-retention choice cannot create new
handoffs until renewed guidance. Lifecycle observations contain metadata, not
worker output bodies. Full Core-work cancellation/purge/migration qualification
remains a development release gate; see LIFECYCLE_AND_PERSISTENCE.md.

### Legacy shared-state removal

Default uninstall preserves shared user/runtime state. `purge` removes all Hermes
Alive-owned shared state and is destructive.
