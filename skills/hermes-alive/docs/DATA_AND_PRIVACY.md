# Data and Privacy

## Local data categories

Hermes Alive may persist:

- managed non-secret personalization;
- bounded conversation/activity context;
- voice and interest profiles;
- proactive delivery and decision logs;
- discovery cache and content evidence;
- dream diffs and memory-processing state;
- Circadian state, intent-bridge state, and shadow observability;
- a confirmed location profile for optional weather context.

The default shared root is:

```text
/opt/data/hermes_alive_shared
```

Runtime paths honor `HERMES_ALIVE_SHARED_DIR` when explicitly set.

## Data minimization

- Provider secrets remain in Hermes configuration.
- Raw user messages are not persisted in Circadian intent or quality-governor
  state.
- Quality observability stores hashes, classifications, bounded counters,
  timestamps, and opaque episode identifiers.
- Logs and JSONL files are bounded or rotated.
- Interest learning does not infer sensitive identity traits.
- Rejected candidate bodies are not written into isolated-enforcement
  observability.

## Location onboarding

Location setup is a small part of normal personalization, not a separate panel.
When no confirmed profile exists, the user may permit one network-assisted
coarse lookup, type a district/county-equivalent place, or skip weather.

The target precision is the finest reliable district, county, borough, suburb,
planning area, or equivalent. The system must not fabricate fine-grained
precision when evidence supports only a city or region.

Network-assisted lookup and geocoding receive only the minimum location input
required by those services. Hermes chat content, user identity, session data,
model credentials, and Provider secrets are not sent. Raw public IP and raw
lookup responses are not persisted.

Only the confirmed profile is stored locally:

- enabled/confirmed flags;
- display name;
- country and administrative levels;
- latitude/longitude;
- timezone;
- source class and precision.

A changed network exit never silently replaces a user-confirmed location.
Weather queries remain disabled until the profile is confirmed and contains
coordinates. There are no fallback coordinates.

## Removal

Default uninstall preserves user/runtime state. `purge` removes all Hermes
Alive-owned shared state. Destructive cleanup must be explicit.
