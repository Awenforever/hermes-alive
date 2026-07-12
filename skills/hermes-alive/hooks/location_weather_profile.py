"""Location and weather onboarding helpers for Hermes Alive.

Markers:
- HERMES_ALIVE_LOCATION_WEATHER_ONBOARDING_V1
- HERMES_ALIVE_LOCATION_PRIVACY_MINIMIZATION_V1
- HERMES_ALIVE_FINE_GRAINED_LOCATION_V1
- HERMES_ALIVE_CHAT_LOCATION_CONFIRMATION_V1

The module keeps onboarding lightweight:
- infer local timezone/locale without terminal questions;
- optionally use one network-assisted lookup during automated installation;
- refine latitude/longitude to a district/county-like address level when data exists;
- let Hermes ask at most one natural-language confirmation in the normal chat;
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



def candidate_from_profile(values: dict[str, Any]) -> LocationCandidate:
    """Rebuild a safe candidate from managed profile values without duplicating labels."""

    admin1 = _text(values.get("weather_admin1"))
    admin2 = _text(values.get("weather_admin2"))
    admin3 = _text(values.get("weather_admin3"))
    location_name = _text(values.get("weather_location_name"))

    # ``weather_location_name`` is normally the already-composed public label.
    # Reusing that full label as ``locality`` duplicates every administrative
    # component when ``display_name`` is reconstructed. Keep it only as a
    # fallback for unresolved free-text locations.
    component_keys = {
        value.casefold()
        for value in (admin1, admin2, admin3)
        if value
    }
    locality = location_name
    if " · " in location_name or location_name.casefold() in component_keys:
        locality = ""

    return LocationCandidate(
        country_code=_text(values.get("weather_country_code")).upper(),
        country_name="",
        admin1=admin1,
        admin2=admin2,
        admin3=admin3,
        locality=locality,
        latitude=_coord(values.get("weather_lat"), latitude=True),
        longitude=_coord(values.get("weather_lon"), latitude=False),
        timezone=_text(values.get("weather_timezone")),
        source=_text(values.get("weather_location_source")) or "managed_profile",
        precision=_text(values.get("weather_location_precision")) or "unknown",
        confidence=1.0 if values.get("weather_location_confirmed") else 0.5,
    )


def prepare_location_onboarding(
    current_values: dict[str, Any],
    *,
    allow_network: bool,
    fetch_json: FetchJson = default_fetch_json,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Prepare one optional chat confirmation without using terminal prompts.

    Installation never blocks on stdin. System timezone/locale are read locally.
    When ``allow_network`` is true, a single coarse network lookup may refine the
    suggestion to a district/county-like level. The candidate stays disabled
    until Hermes asks the user once in the normal chat and applies the answer.
    """

    values = dict(current_values)
    if values.get("weather_location_confirmed"):
        values["weather_onboarding_complete"] = True
        return values
    if values.get("weather_onboarding_complete"):
        return values

    system = infer_system_location(environ)
    candidate = system
    if allow_network:
        try:
            candidate = infer_network_location(
                fetch_json=fetch_json,
                language=(detect_system_locale(environ) or "en").split("_", 1)[0],
                system_candidate=system,
            )
        except Exception:
            candidate = system

    values.update(profile_values(candidate, confirmed=False, enabled=False))
    values["weather_onboarding_complete"] = False
    return values


def confirm_location_onboarding(
    current_values: dict[str, Any],
    *,
    user_location: str = "",
    fetch_json: FetchJson = default_fetch_json,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Apply the user's one chat answer and finish weather onboarding."""

    values = dict(current_values)
    system = infer_system_location(environ)
    candidate = candidate_from_profile(values)
    location_text = _text(user_location)

    if location_text:
        try:
            candidate = geocode_location_text(
                location_text,
                fetch_json=fetch_json,
                language=(detect_system_locale(environ) or "en").split("_", 1)[0],
                timezone=candidate.timezone or system.timezone,
            )
        except Exception:
            candidate = LocationCandidate(
                locality=location_text,
                timezone=candidate.timezone or system.timezone,
                source="manual_correction_unresolved",
                precision="user_text",
                confidence=0.4,
            )
    elif not candidate.has_coordinates and candidate.display_name:
        try:
            candidate = geocode_location_text(
                candidate.display_name,
                fetch_json=fetch_json,
                language=(detect_system_locale(environ) or "en").split("_", 1)[0],
                timezone=candidate.timezone or system.timezone,
            )
        except Exception:
            pass

    values.update(profile_values(candidate, confirmed=True))
    values["weather_onboarding_complete"] = True
    return values


def disable_location_onboarding(
    current_values: dict[str, Any],
) -> dict[str, Any]:
    """Finish onboarding without weather context."""

    values = dict(current_values)
    values["weather_enabled"] = False
    values["weather_location_confirmed"] = False
    values["weather_onboarding_complete"] = True
    return values


def location_confirmation_prompt(values: dict[str, Any]) -> str:
    """Return one natural-language question for Hermes to ask in chat."""

    candidate = candidate_from_profile(values)
    name = (
        _text(values.get("weather_location_name"))
        or candidate.display_name
        or candidate.timezone
    )
    if name:
        if candidate.source.startswith("network"):
            basis = "我根据系统时区和网络出口做了粗略判断"
            privacy = "粗定位只会向定位服务发送网络出口 IP"
        else:
            basis = "我根据系统时区做了粗略判断"
            privacy = "这一步没有读取聊天内容"
        return (
            f"{basis}，你可能在 {name}。以后天气先按这里查询，可以吗？"
            "如果不对，直接告诉我所在的区、县或同等级别区域就行；"
            f"{privacy}，天气查询只发送必要的地区或坐标。"
        )
    return (
        "我没能可靠判断你所在的地区。为了让天气提醒更准确，"
        "可以告诉我所在的区、县或同等级别区域吗？不想提供也没关系，"
        "我会保持天气功能关闭。"
    )

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
