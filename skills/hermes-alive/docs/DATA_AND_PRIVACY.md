# Data and Privacy

## Local data categories

Hermes Alive may persist:

- managed non-secret configuration;
- bounded conversation and activity context;
- voice and interest profiles;
- proactive delivery and decision logs;
- Discovery cache and content evidence;
- topic reservation and delivery history;
- dream diffs and memory-processing state;
- Circadian state and shadow observability;
- an optional confirmed location profile.

The lifecycle default shared root is:

```text
$HERMES_HOME/hermes_alive_shared
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
- Logs and JSONL files are bounded or rotated.
- Interest learning does not infer sensitive identity traits.

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
