# Hermes Alive — Development Memorandum

Internal engineering notes. User-facing README files describe the product;
failure history and non-regression constraints live here.

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
