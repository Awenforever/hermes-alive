#!/usr/bin/env python3
"""Deterministic tests for zero-touch Location & Weather Onboarding v2."""

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
    confirm_location_onboarding,
    contains_raw_ip,
    disable_location_onboarding,
    infer_network_location,
    infer_system_location,
    location_confirmation_prompt,
    prepare_location_onboarding,
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


def lifecycle_command(home: Path, shared: Path, *extra: str) -> list[str]:
    return [
        sys.executable,
        str(ROOT / "scripts" / "hermes-alive-lifecycle.py"),
        "configure",
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
        *extra,
    ]


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


def test_prepare_network_suggestion_is_zero_touch() -> None:
    values = prepare_location_onboarding(
        {},
        allow_network=True,
        fetch_json=fake_fetch,
        environ={"TZ": "Asia/Singapore", "LANG": "en_SG.UTF-8"},
    )
    check(values["weather_location_confirmed"] is False, "candidate auto-confirmed")
    check(values["weather_enabled"] is False, "weather enabled before chat confirmation")
    check(values["weather_admin3"] == "Tampines", "district suggestion missing")
    check(values["weather_onboarding_complete"] is False, "pending onboarding marked complete")
    check(not contains_raw_ip(values), "raw IP persisted")


def test_chat_prompt_is_natural_and_single_question() -> None:
    values = prepare_location_onboarding(
        {},
        allow_network=True,
        fetch_json=fake_fetch,
        environ={"TZ": "Asia/Singapore", "LANG": "zh_CN.UTF-8"},
    )
    prompt = location_confirmation_prompt(values)
    check("Tampines" in prompt, "district missing from chat prompt")
    check(prompt.count("Tampines") == 1, "district duplicated in chat prompt")
    check(prompt.count("Singapore") == 1, "country/city duplicated in chat prompt")
    check(prompt.count("？") == 1, "chat onboarding should ask one question")
    for forbidden in (
        "Timezone [",
        "Quiet hours",
        "Weather location (",
        "Y/n",
        "--weather",
    ):
        check(forbidden not in prompt, f"terminal jargon leaked: {forbidden}")


def test_confirm_existing_suggestion() -> None:
    pending = prepare_location_onboarding(
        {},
        allow_network=True,
        fetch_json=fake_fetch,
        environ={"TZ": "Asia/Singapore"},
    )
    values = confirm_location_onboarding(
        pending,
        fetch_json=fake_fetch,
        environ={"TZ": "Asia/Singapore"},
    )
    check(values["weather_location_confirmed"] is True, "suggestion not confirmed")
    check(values["weather_enabled"] is True, "confirmed coordinates did not enable weather")
    check(values["weather_onboarding_complete"] is True, "onboarding not completed")


def test_manual_chat_correction() -> None:
    pending = prepare_location_onboarding(
        {},
        allow_network=True,
        fetch_json=fake_fetch,
        environ={"TZ": "Asia/Singapore"},
    )
    values = confirm_location_onboarding(
        pending,
        user_location="Jurong East",
        fetch_json=fake_fetch,
        environ={"TZ": "Asia/Singapore", "LANG": "en_SG.UTF-8"},
    )
    check(values["weather_admin3"] == "Jurong East", "manual district not resolved")
    check(values["weather_location_source"] == "manual_text_geocoded", "source class wrong")
    check(values["weather_onboarding_complete"] is True, "manual correction not completed")


def test_disable_weather_finishes_onboarding() -> None:
    pending = prepare_location_onboarding(
        {},
        allow_network=True,
        fetch_json=fake_fetch,
        environ={"TZ": "Asia/Singapore"},
    )
    values = disable_location_onboarding(pending)
    check(values["weather_enabled"] is False, "weather remained enabled")
    check(values["weather_location_confirmed"] is False, "disabled location marked confirmed")
    check(values["weather_onboarding_complete"] is True, "disable did not finish onboarding")


def test_lifecycle_zero_touch_defaults() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        shared = home / "shared"
        env = dict(os.environ)
        env["TZ"] = "Asia/Singapore"
        result = subprocess.run(
            lifecycle_command(home, shared),
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            env=env,
            check=False,
        )
        check(result.returncode == 0, f"configure failed: {result.stdout} {result.stderr}")
        for forbidden in (
            "Timezone [system default]",
            "Quiet hours start",
            "Quiet hours end",
            "Weather location (",
            "Enable Hermes Alive now",
        ):
            check(forbidden not in result.stdout, f"terminal prompt leaked: {forbidden}")
        check("HERMES_ALIVE_ZERO_TOUCH_CONFIG_OK" in result.stdout, "zero-touch marker missing")
        payload = json.loads((shared / "config" / "hermes-alive.json").read_text())
        values = payload["values"]
        check(payload["config_version"] == 4, "config version not upgraded")
        check(values["enabled"] is False, "safe default should remain disabled")
        check(values["timezone"] == "Asia/Singapore", "timezone not auto-detected")
        check(values["circadian_timezone"] == "Asia/Singapore", "circadian timezone diverged")
        check(values["quiet_start"] == "23:00", "quiet start default missing")
        check(values["quiet_end"] == "08:00", "quiet end default missing")
        check(values["weather_enabled"] is False, "weather enabled without confirmation")


def test_lifecycle_structured_profile_is_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        shared = home / "shared"
        command = lifecycle_command(
            home,
            shared,
            "--non-interactive",
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
        )
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        check(result.returncode == 0, f"configure failed: {result.stdout} {result.stderr}")
        payload = json.loads((shared / "config" / "hermes-alive.json").read_text())
        values = payload["values"]
        check(payload["config_version"] == 4, "config version wrong")
        check(values["weather_admin3"] == "Tampines", "district not persisted")
        check(values["weather_location_confirmed"] is True, "confirmation not persisted")
        check(values["weather_onboarding_complete"] is True, "onboarding completion missing")
        check(values["timezone"] == "Asia/Singapore", "confirmed timezone not adopted")
        check(not contains_raw_ip(payload), "managed config contains raw IP")


def test_lifecycle_confirms_existing_candidate_without_prompt() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        shared = home / "shared"
        config = shared / "config" / "hermes-alive.json"
        config.parent.mkdir(parents=True)
        config.write_text(
            json.dumps(
                {
                    "config_version": 4,
                    "values": {
                        "weather_enabled": False,
                        "weather_location_confirmed": False,
                        "weather_onboarding_complete": False,
                        "weather_location_name": "Singapore · Tampines",
                        "weather_admin3": "Tampines",
                        "weather_timezone": "Asia/Singapore",
                        "weather_lat": "1.352100",
                        "weather_lon": "103.944000",
                    },
                }
            ),
            encoding="utf-8",
        )
        result = subprocess.run(
            lifecycle_command(
                home,
                shared,
                "--non-interactive",
                "--weather-location-confirmed",
            ),
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        check(result.returncode == 0, f"confirm failed: {result.stdout} {result.stderr}")
        values = json.loads(config.read_text())["values"]
        check(values["weather_enabled"] is True, "confirmed candidate not enabled")
        check(values["weather_onboarding_complete"] is True, "confirmation not completed")
        check("location_confirmation_required=false" in result.stdout, "still asks location")


def test_lifecycle_skip_weather_is_final() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / "home"
        shared = home / "shared"
        result = subprocess.run(
            lifecycle_command(home, shared, "--non-interactive", "--skip-weather"),
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            check=False,
        )
        check(result.returncode == 0, f"skip failed: {result.stdout} {result.stderr}")
        values = json.loads((shared / "config" / "hermes-alive.json").read_text())["values"]
        check(values["weather_enabled"] is False, "skip enabled weather")
        check(values["weather_onboarding_complete"] is True, "skip not persisted")
        check("location_confirmation_required=false" in result.stdout, "skip asks again")


def test_managed_config_exports_location_context() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        shared = Path(tmp)
        config = shared / "config" / "hermes-alive.json"
        config.parent.mkdir(parents=True)
        config.write_text(
            json.dumps(
                {
                    "config_version": 4,
                    "values": {
                        "weather_enabled": True,
                        "weather_location_confirmed": True,
                        "weather_onboarding_complete": True,
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
        test_prepare_network_suggestion_is_zero_touch,
        test_chat_prompt_is_natural_and_single_question,
        test_confirm_existing_suggestion,
        test_manual_chat_correction,
        test_disable_weather_finishes_onboarding,
        test_lifecycle_zero_touch_defaults,
        test_lifecycle_structured_profile_is_safe,
        test_lifecycle_confirms_existing_candidate_without_prompt,
        test_lifecycle_skip_weather_is_final,
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
