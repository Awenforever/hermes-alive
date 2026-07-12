"""Location and weather onboarding helpers for Hermes Alive.

Markers:
- HERMES_ALIVE_LOCATION_WEATHER_ONBOARDING_V1
- HERMES_ALIVE_LOCATION_PRIVACY_MINIMIZATION_V1
- HERMES_ALIVE_FINE_GRAINED_LOCATION_V1

The module keeps onboarding lightweight:
- infer local timezone/locale without network access;
- optionally use one network-assisted lookup after the user selects it;
- refine latitude/longitude to a district/county-like address level when data exists;
- require confirmation before a profile is marked usable;
- persist no public IP and no raw lookup response.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

IP_GEO_URL = "https://ipapi.co/json/"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "hermes-alive-location-onboarding/1.0"

FetchJson = Callable[[str, float], Any]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not (-90.0 <= number <= 90.0) and not (-180.0 <= number <= 180.0):
        return None
    return number


def _coord(value: Any, *, latitude: bool) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    low, high = (-90.0, 90.0) if latitude else (-180.0, 180.0)
    return number if low <= number <= high else None


def _unique(parts: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for part in parts:
        value = _text(part)
        key = value.casefold()
        if not value or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


@dataclass(frozen=True)
class LocationCandidate:
    country_code: str = ""
    country_name: str = ""
    admin1: str = ""
    admin2: str = ""
    admin3: str = ""
    locality: str = ""
    latitude: float | None = None
    longitude: float | None = None
    timezone: str = ""
    source: str = "system"
    precision: str = "unknown"
    confidence: float = 0.0

    @property
    def display_name(self) -> str:
        parts = _unique(
            [self.country_name, self.admin1, self.admin2, self.admin3, self.locality]
        )
        return " · ".join(parts)

    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    def to_safe_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["display_name"] = self.display_name
        payload["has_coordinates"] = self.has_coordinates
        return payload


def detect_system_timezone(
    environ: dict[str, str] | None = None,
    *,
    timezone_file: Path = Path("/etc/timezone"),
    localtime_path: Path = Path("/etc/localtime"),
) -> str:
    env = os.environ if environ is None else environ
    configured = _text(env.get("TZ"))
    if configured and "/" in configured:
        return configured
    try:
        value = timezone_file.read_text(encoding="utf-8").strip()
        if value and "/" in value:
            return value
    except OSError:
        pass
    try:
        resolved = localtime_path.resolve()
        marker = "/zoneinfo/"
        text = str(resolved)
        if marker in text:
            return text.split(marker, 1)[1]
    except OSError:
        pass
    return configured


def detect_system_locale(environ: dict[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    for key in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = _text(env.get(key))
        if value:
            return value.split(".", 1)[0]
    return ""


def infer_system_location(environ: dict[str, str] | None = None) -> LocationCandidate:
    timezone = detect_system_timezone(environ)
    locale_name = detect_system_locale(environ)
    country_code = ""
    country_name = ""
    admin1 = ""
    locality = ""

    if timezone == "Asia/Singapore":
        country_code = "SG"
        country_name = "Singapore"
        admin1 = "Singapore"
        locality = "Singapore"
    elif timezone:
        area, _, place = timezone.partition("/")
        locality = place.replace("_", " ") if place else ""
        if area == "Asia" and locale_name.lower().endswith(("_cn", "_sg", "_tw", "_hk")):
            country_code = locale_name.rsplit("_", 1)[-1].upper()

    return LocationCandidate(
        country_code=country_code,
        country_name=country_name,
        admin1=admin1,
        locality=locality,
        timezone=timezone,
        source="system_timezone_locale",
        precision="city_or_timezone",
        confidence=0.35 if locality else 0.15,
    )


def default_fetch_json(url: str, timeout: float = 5.0) -> Any:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read(512 * 1024)
    return json.loads(body.decode("utf-8", errors="strict"))


def _address_candidate(
    address: dict[str, Any],
    *,
    latitude: float | None,
    longitude: float | None,
    timezone: str,
    source: str,
    fallback: LocationCandidate | None = None,
) -> LocationCandidate:
    fallback = fallback or LocationCandidate()
    country_code = _text(address.get("country_code") or fallback.country_code).upper()
    country_name = _text(address.get("country") or fallback.country_name)
    admin1 = _text(
        address.get("state")
        or address.get("province")
        or address.get("region")
        or fallback.admin1
    )
    admin2 = _text(
        address.get("county")
        or address.get("state_district")
        or address.get("municipality")
        or fallback.admin2
    )
    admin3 = _text(
        address.get("city_district")
        or address.get("borough")
        or address.get("district")
        or address.get("suburb")
        or fallback.admin3
    )
    locality = _text(
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("quarter")
        or address.get("neighbourhood")
        or fallback.locality
    )
    precision = "district_or_county" if (admin3 or admin2) else "city"
    confidence = 0.78 if admin3 else (0.70 if admin2 else 0.58)
    return LocationCandidate(
        country_code=country_code,
        country_name=country_name,
        admin1=admin1,
        admin2=admin2,
        admin3=admin3,
        locality=locality,
        latitude=latitude,
        longitude=longitude,
        timezone=_text(timezone or fallback.timezone),
        source=source,
        precision=precision,
        confidence=confidence,
    )


def infer_network_location(
    *,
    fetch_json: FetchJson = default_fetch_json,
    timeout: float = 5.0,
    language: str = "en",
    system_candidate: LocationCandidate | None = None,
) -> LocationCandidate:
    system = system_candidate or infer_system_location()
    payload = fetch_json(IP_GEO_URL, timeout)
    if not isinstance(payload, dict):
        raise RuntimeError("network geolocation returned invalid payload")
    if payload.get("error"):
        raise RuntimeError("network geolocation lookup failed")
    latitude = _coord(payload.get("latitude"), latitude=True)
    longitude = _coord(payload.get("longitude"), latitude=False)
    base = LocationCandidate(
        country_code=_text(payload.get("country_code")).upper(),
        country_name=_text(payload.get("country_name")),
        admin1=_text(payload.get("region")),
        locality=_text(payload.get("city")),
        latitude=latitude,
        longitude=longitude,
        timezone=_text(payload.get("timezone") or system.timezone),
        source="network_ip_coarse",
        precision="city",
        confidence=0.52,
    )
    if latitude is None or longitude is None:
        return base if base.display_name else system

    query = urllib.parse.urlencode(
        {
            "format": "jsonv2",
            "lat": f"{latitude:.6f}",
            "lon": f"{longitude:.6f}",
            "zoom": "14",
            "addressdetails": "1",
            "accept-language": language or "en",
        }
    )
    try:
        reverse = fetch_json(f"{NOMINATIM_REVERSE_URL}?{query}", timeout)
        address = reverse.get("address") if isinstance(reverse, dict) else None
        if isinstance(address, dict):
            return _address_candidate(
                address,
                latitude=latitude,
                longitude=longitude,
                timezone=base.timezone,
                source="network_ip_plus_reverse_geocode",
                fallback=base,
            )
    except Exception:
        pass
    return base


def geocode_location_text(
    text: str,
    *,
    fetch_json: FetchJson = default_fetch_json,
    timeout: float = 5.0,
    language: str = "en",
    timezone: str = "",
) -> LocationCandidate:
    query_text = _text(text)
    if not query_text:
        return LocationCandidate(timezone=timezone, source="manual_empty")
    query = urllib.parse.urlencode(
        {
            "format": "jsonv2",
            "q": query_text,
            "limit": "1",
            "addressdetails": "1",
            "accept-language": language or "en",
        }
    )
    payload = fetch_json(f"{NOMINATIM_SEARCH_URL}?{query}", timeout)
    if isinstance(payload, dict):
        rows = payload.get("results")
    else:
        rows = payload
    if not isinstance(rows, list) or not rows:
        return LocationCandidate(
            locality=query_text,
            timezone=timezone,
            source="manual_text_unresolved",
            precision="user_text",
            confidence=0.4,
        )
    row = rows[0] if isinstance(rows[0], dict) else {}
    address = row.get("address") if isinstance(row.get("address"), dict) else {}
    latitude = _coord(row.get("lat"), latitude=True)
    longitude = _coord(row.get("lon"), latitude=False)
    candidate = _address_candidate(
        address,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        source="manual_text_geocoded",
    )
    if not candidate.display_name:
        candidate = LocationCandidate(
            locality=_text(row.get("display_name")) or query_text,
            latitude=latitude,
            longitude=longitude,
            timezone=timezone,
            source="manual_text_geocoded",
            precision="user_text",
            confidence=0.65,
        )
    return candidate


def profile_values(
    candidate: LocationCandidate,
    *,
    confirmed: bool,
    enabled: bool | None = None,
) -> dict[str, Any]:
    weather_enabled = candidate.has_coordinates if enabled is None else bool(enabled)
    if not confirmed:
        weather_enabled = False
    values: dict[str, Any] = {
        "weather_enabled": weather_enabled,
        "weather_location_confirmed": bool(confirmed),
        "weather_location_name": candidate.display_name,
        "weather_country_code": candidate.country_code,
        "weather_admin1": candidate.admin1,
        "weather_admin2": candidate.admin2,
        "weather_admin3": candidate.admin3,
        "weather_timezone": candidate.timezone,
        "weather_location_source": candidate.source,
        "weather_location_precision": candidate.precision,
    }
    if candidate.latitude is not None:
        values["weather_lat"] = f"{candidate.latitude:.6f}"
    if candidate.longitude is not None:
        values["weather_lon"] = f"{candidate.longitude:.6f}"
    return values


def _is_skip(text: str) -> bool:
    return _text(text).casefold() in {"skip", "no", "n", "off", "disable", "不用", "跳过", "关闭"}


def interactive_location_onboarding(
    current_values: dict[str, Any],
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    fetch_json: FetchJson = default_fetch_json,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a compact, one-feature onboarding embedded in normal configure.

    First prompt: Enter means network-assisted inference; a typed place means manual
    geocoding; skip disables weather. The prompt itself explains the external data
    boundary. A second prompt confirms or corrects the candidate.
    """

    values = dict(current_values)
    if values.get("weather_location_confirmed"):
        return values
    system = infer_system_location(environ)
    hint = system.display_name or system.timezone or "system location unavailable"
    choice = input_fn(
        "Weather location (Enter=network-assisted inference; type district/county="
        "manual; skip=off). Only the network exit IP or typed place is sent to "
        f"location services; chat content is never sent. System hint: {hint}: "
    ).strip()
    if _is_skip(choice):
        values.update(profile_values(system, confirmed=False, enabled=False))
        return values

    try:
        if choice:
            candidate = geocode_location_text(
                choice,
                fetch_json=fetch_json,
                language=(detect_system_locale(environ) or "en").split("_", 1)[0],
                timezone=system.timezone,
            )
        else:
            candidate = infer_network_location(
                fetch_json=fetch_json,
                language=(detect_system_locale(environ) or "en").split("_", 1)[0],
                system_candidate=system,
            )
    except Exception as exc:
        output_fn(f"Location inference unavailable: {type(exc).__name__}")
        candidate = system

    name = candidate.display_name or candidate.timezone or "unknown location"
    answer = input_fn(
        f"Use {name} for local weather? [Y/n or type a corrected district/county]: "
    ).strip()
    if _is_skip(answer):
        values.update(profile_values(candidate, confirmed=False, enabled=False))
        return values
    if answer and answer.casefold() not in {"y", "yes", "ok", "是", "可以"}:
        try:
            candidate = geocode_location_text(
                answer,
                fetch_json=fetch_json,
                language=(detect_system_locale(environ) or "en").split("_", 1)[0],
                timezone=candidate.timezone or system.timezone,
            )
        except Exception:
            candidate = LocationCandidate(
                locality=answer,
                timezone=candidate.timezone or system.timezone,
                source="manual_correction_unresolved",
                precision="user_text",
                confidence=0.4,
            )
    values.update(profile_values(candidate, confirmed=True))
    return values


def safe_location_summary(values: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "weather_enabled",
        "weather_location_confirmed",
        "weather_location_name",
        "weather_country_code",
        "weather_admin1",
        "weather_admin2",
        "weather_admin3",
        "weather_timezone",
        "weather_location_source",
        "weather_location_precision",
        "weather_lat",
        "weather_lon",
    }
    return {key: values.get(key) for key in sorted(allowed) if key in values}


def contains_raw_ip(payload: Any) -> bool:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return bool(re.search(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)", text))
