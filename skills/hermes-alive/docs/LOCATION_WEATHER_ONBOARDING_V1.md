# Hermes Alive Location & Weather Onboarding v1

Markers:

- `HERMES_ALIVE_LOCATION_WEATHER_ONBOARDING_V1`
- `HERMES_ALIVE_LOCATION_PRIVACY_MINIMIZATION_V1`
- `HERMES_ALIVE_FINE_GRAINED_LOCATION_V1`

## Role in the architecture

This capability is a lightweight part of the existing lifecycle `configure` flow. It does not replace Circadian Engine, Sleep / Quiet Policy, or Proactive Quality Governor.

Decision order remains:

1. Circadian Engine
2. Sleep / Quiet Policy
3. Proactive Quality Governor
4. Composer context providers, including confirmed local weather
5. Existing delivery, Weixin routing and footer handling

## Onboarding behavior

The interactive lifecycle asks one compact weather-location question only when no confirmed profile exists:

- press Enter: permit one network-assisted coarse lookup and reverse-geocode refinement;
- type a district/county or equivalent local area: geocode that text;
- type `skip`: leave weather disabled.

A second short prompt confirms or corrects the candidate. No separate matrix of weather toggles is shown.

The target precision is the finest reliable administrative/local level available, normally district, county, borough, suburb, planning area or equivalent. The system must not invent a fine-grained area when lookup evidence only supports a city or region.

## Privacy contract

- Local timezone and locale are read without network access.
- Network-assisted inference occurs only after the user selects that option.
- The network exit IP is sent only to the coarse IP-location service as part of the request.
- Reverse geocoding receives only latitude/longitude.
- Manual correction sends only the typed place name to geocoding.
- No chat content, user name, Weixin identity, Hermes session, model credential or Provider secret is sent.
- The raw public IP and raw lookup responses are never persisted.
- Only the confirmed profile, coordinates, precision and source class are stored locally.

## Weather perspective contract

Weather context is disabled unless coordinates exist and the profile is confirmed. There are no fallback coordinates.

Allowed examples:

- `接下来一周好像都有雨。`
- `下午可能有雷暴，晚点出门记得带伞。`
- `怎么又下雨了。`

Forbidden examples:

- `我这儿在下雨。`
- `我快热死了。`
- `雷暴闷得我喘不过气。`

The bot may offer reminders, care or light commentary, but may not claim a physical location or bodily weather experience.

## Persistence

Managed configuration stores only:

- enabled / confirmed flags;
- display name;
- country and administrative levels;
- latitude / longitude;
- timezone;
- source class and precision.

Changing network exit location never silently overwrites a previously confirmed profile.
