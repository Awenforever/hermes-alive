#!/usr/bin/env python3
"""Deterministic tests for Location & Weather Onboarding v1."""

from __future__ import annotations

import asyncio
import importlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
SCRIPTS = ROOT / "scripts"
for path in (HOOKS, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from location_weather_profile import (  # noqa: E402
    IP_GEO_URL,
    NOMINATIM_REVERSE_URL,
    NOMINATIM_SEARCH_URL,
    LocationCandidate,
    contains_raw_ip,
    infer_network_location,
    infer_system_location,
    interactive_location_onboarding,
    profile_values,
    safe_location_summary,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def fake_fetch(url: str, timeout: float):
    del timeout
    if url == IP_GEO_URL:
        return {
            "ip": "203.0.113.9",
            "city": "Singapore",
            "region": "Singapore",
            "country_code": "SG",
            "country_name": "Singapore",
            "latitude": 1.3521,
            "longitude": 103.944,
            "timezone": "Asia/Singapore",
        }
    if url.startswith(NOMINATIM_REVERSE_URL):
        return {
            "address": {
                "country": "Singapore",
                "country_code": "sg",
                "state": "Singapore",
                "city_district": "Tampines",
                "city": "Singapore",
            }
        }
    if url.startswith(NOMINATIM_SEARCH_URL):
        return [
            {
                "lat": "1.3329",
                "lon": "103.7436",
                "display_name": "Jurong East, Singapore",
                "address": {
                    "country": "Singapore",
                    "country_code": "sg",
                    "state": "Singapore",
                    "city_district": "Jurong East",
                    "city": "Singapore",
                },
            }
        ]
    raise AssertionError(f"unexpected URL: {url}")


def test_system_timezone_inference() -> None:
    candidate = infer_system_location({"TZ": "Asia/Singapore", "LANG": "en_SG.UTF-8"})
    check(candidate.timezone == "Asia/Singapore", "timezone not detected")
    check(candidate.country_code == "SG", "Singapore country not inferred")
    check(candidate.precision == "city_or_timezone", "system precision overstated")


def test_network_lookup_refines_to_district() -> None:
    candidate = infer_network_location(
        fetch_json=fake_fetch,
        system_candidate=LocationCandidate(timezone="Asia/Singapore"),
    )
    check(candidate.admin3 == "Tampines", "district was not extracted")
    check(candidate.precision == "district_or_county", "fine-grained precision missing")
    check(candidate.has_coordinates, "coordinates missing")
    check("Tampines" in candidate.display_name, "display name missing district")


def test_profile_is_confirmation_gated_and_ip_free() -> None:
    candidate = infer_network_location(fetch_json=fake_fetch)
    unconfirmed = profile_values(candidate, confirmed=False)
    confirmed = profile_values(candidate, confirmed=True)
    check(unconfirmed["weather_enabled"] is False, "unconfirmed weather was enabled")
    check(confirmed["weather_enabled"] is True, "confirmed coordinates did not enable weather")
    check(not contains_raw_ip(confirmed), "raw IP persisted")
    summary = safe_location_summary(confirmed)
    check("203.0.113.9" not in json.dumps(summary), "raw IP leaked into summary")


def test_interactive_network_inference_is_compact() -> None:
    answers = iter(["", "y"])
    prompts: list[str] = []
    values = interactive_location_onboarding(
        {},
        input_fn=lambda prompt: prompts.append(prompt) or next(answers),
        output_fn=lambda text: None,
        fetch_json=fake_fetch,
        environ={"TZ": "Asia/Singapore", "LANG": "en_SG.UTF-8"},
    )
    check(len(prompts) == 2, "onboarding should use two compact prompts")
    check(values["weather_location_confirmed"] is True, "candidate not confirmed")
    check(values["weather_admin3"] == "Tampines", "district not stored")


def test_interactive_manual_correction() -> None:
    answers = iter(["Jurong East", "y"])
    values = interactive_location_onboarding(
        {},
        input_fn=lambda prompt: next(answers),
        output_fn=lambda text: None,
        fetch_json=fake_fetch,
        environ={"TZ": "Asia/Singapore", "LANG": "en_SG.UTF-8"},
    )
    check(values["weather_admin3"] == "Jurong East", "manual district not resolved")
    check(values["weather_location_source"] == "manual_text_geocoded", "source class wrong")


def test_interactive_skip_disables_weather() -> None:
    values = interactive_location_onboarding(
        {},
        input_fn=lambda prompt: "skip",
        output_fn=lambda text: None,
        fetch_json=fake_fetch,
        environ={"TZ": "Asia/Singapore"},
    )
    check(values["weather_enabled"] is False, "skip did not disable weather")
    check(values["weather_location_confirmed"] is False, "skip unexpectedly confirmed")


def test_lifecycle_noninteractive_persists_only_safe_profile() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        shared = home / "shared"
        command = [
            sys.executable,
            str(ROOT / "scripts" / "hermes-alive-lifecycle.py"),
            "configure",
            "--non-interactive",
            "--source-root",
            str(ROOT),
            "--hermes-home",
            str(home),
            "--source-target",
            str(home / "skills" / "hermes" / "hermes-alive"),
            "--hook-target",
            str(home / "hooks" / "hermes-alive"),
            "--shared-dir",
            str(shared),
            "--weather-enabled",
            "--weather-location-confirmed",
            "--weather-location",
            "Singapore",
            "--weather-country-code",
            "SG",
            "--weather-admin1",
            "Singapore",
            "--weather-admin3",
            "Tampines",
            "--weather-timezone",
            "Asia/Singapore",
            "--weather-lat",
            "1.352100",
            "--weather-lon",
            "103.944000",
        ]
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        check(result.returncode == 0, f"configure failed: {result.stdout} {result.stderr}")
        payload = json.loads((shared / "config" / "hermes-alive.json").read_text())
        values = payload["values"]
        check(payload["config_version"] == 3, "config version not upgraded")
        check(values["weather_admin3"] == "Tampines", "district not persisted")
        check(values["weather_location_confirmed"] is True, "confirmation not persisted")
        check(not contains_raw_ip(payload), "managed config contains raw IP")


def test_managed_config_exports_location_context() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        shared = Path(tmp)
        config = shared / "config" / "hermes-alive.json"
        config.parent.mkdir(parents=True)
        config.write_text(
            json.dumps(
                {
                    "config_version": 3,
                    "values": {
                        "weather_enabled": True,
                        "weather_location_confirmed": True,
                        "weather_location_name": "Singapore · Tampines",
                        "weather_admin3": "Tampines",
                        "weather_timezone": "Asia/Singapore",
                        "weather_lat": "1.352100",
                        "weather_lon": "103.944000",
                    },
                }
            )
        )
        old = dict(os.environ)
        try:
            os.environ["HERMES_ALIVE_SHARED_DIR"] = str(shared)
            for key in list(os.environ):
                if key.startswith("HERMES_PROACTIVE_WEATHER_") or key in {
                    "HERMES_PROACTIVE_LAT",
                    "HERMES_PROACTIVE_LON",
                }:
                    os.environ.pop(key, None)
            import managed_config
            importlib.reload(managed_config)
            loaded = managed_config.load_managed_env(overwrite=True)
            check(loaded["HERMES_PROACTIVE_WEATHER_ADMIN3"] == "Tampines", "admin3 env missing")
            check(loaded["HERMES_PROACTIVE_WEATHER_LOCATION_CONFIRMED"] == "true", "confirmation env missing")
        finally:
            os.environ.clear()
            os.environ.update(old)


def test_weather_composer_has_no_default_coordinates() -> None:
    old = dict(os.environ)
    try:
        for key in (
            "HERMES_PROACTIVE_LAT",
            "HERMES_PROACTIVE_LON",
            "HERMES_PROACTIVE_WEATHER_LOCATION_CONFIRMED",
        ):
            os.environ.pop(key, None)
        import llm_message_composer
        result = asyncio.run(llm_message_composer._get_weather())
        check(result == "", "composer used fallback coordinates")
    finally:
        os.environ.clear()
        os.environ.update(old)


def main() -> int:
    tests = [
        test_system_timezone_inference,
        test_network_lookup_refines_to_district,
        test_profile_is_confirmation_gated_and_ip_free,
        test_interactive_network_inference_is_compact,
        test_interactive_manual_correction,
        test_interactive_skip_disables_weather,
        test_lifecycle_noninteractive_persists_only_safe_profile,
        test_managed_config_exports_location_context,
        test_weather_composer_has_no_default_coordinates,
    ]
    failures: list[str] = []
    for test in tests:
        try:
            test()
            print(f"LOCATION_WEATHER_PASS {test.__name__}")
        except Exception as exc:
            failures.append(f"{test.__name__}:{type(exc).__name__}:{exc}")
            print(f"LOCATION_WEATHER_FAIL {failures[-1]}")
    print(json.dumps({"tests": len(tests), "failures": failures}, ensure_ascii=False))
    if failures:
        return 1
    print("HERMES_ALIVE_LOCATION_WEATHER_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
