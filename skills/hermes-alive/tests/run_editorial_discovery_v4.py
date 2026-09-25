#!/usr/bin/env python3
"""Regression contracts for diverse, fresh Alive editorial discovery."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from discovery import DiscoveryEngine, ExternalDiscovery, _score_item  # noqa: E402


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def candidate(lane: str, index: int, *, score: float = 0.8) -> dict:
    return {
        "source": "news_search" if lane != "academic" else "arxiv",
        "lane": lane,
        "title": f"{lane}-{index}",
        "url": f"https://example.invalid/{lane}/{index}",
        "score": score,
    }


def test_no_academic_source_bonus() -> None:
    common = {"title": "同等质量候选", "url": "https://example.invalid/x"}
    academic = _score_item({**common, "source": "arxiv", "lane": "academic"})
    local = _score_item({**common, "source": "news_search", "lane": "local_hefei"})
    check(academic == local, f"academic bias remains: {academic} != {local}")


def test_stale_current_affairs_is_rejected() -> None:
    engine = DiscoveryEngine.__new__(DiscoveryEngine)
    engine._sources_config = {"freshness": {"current_affairs": 72}}
    item = candidate("current_affairs", 1)
    item["published_at"] = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    check(not engine._fresh_enough(item), "stale current-affairs item survived")


def test_lanes_are_interleaved_and_capped() -> None:
    engine = DiscoveryEngine.__new__(DiscoveryEngine)
    engine._sources_config = {
        "budgets": {
            "max_per_run": 6,
            "max_per_source": 20,
            "max_per_lane": 3,
            "lane_caps": {"academic": 1},
        },
        "editorial": {
            "lane_order": ["current_affairs", "local_hefei", "social_fun", "academic"]
        },
    }
    ranked = (
        [candidate("academic", i, score=0.99 - i * 0.01) for i in range(5)]
        + [candidate("current_affairs", i) for i in range(3)]
        + [candidate("local_hefei", i) for i in range(3)]
        + [candidate("social_fun", i) for i in range(3)]
    )
    result = engine._enforce_budget(ranked)
    lanes = [item["lane"] for item in result]
    check(len(result) == 6, f"wrong total: {len(result)}")
    check(lanes[:4] == ["current_affairs", "local_hefei", "social_fun", "academic"], lanes)
    check(lanes.count("academic") == 1, f"academic cap failed: {lanes}")


def test_proxy_is_opt_in_and_applied() -> None:
    discovery = ExternalDiscovery({"network": {"proxy_url": "http://proxy.invalid:7890"}})

    class Session:
        def get(self, url, **kwargs):
            return url, kwargs

    url, kwargs = discovery._request(Session(), "https://example.invalid")
    check(url == "https://example.invalid", "request URL changed")
    check(kwargs.get("proxy") == "http://proxy.invalid:7890", f"proxy missing: {kwargs}")


def main() -> int:
    tests = [
        test_no_academic_source_bonus,
        test_stale_current_affairs_is_rejected,
        test_lanes_are_interleaved_and_capped,
        test_proxy_is_opt_in_and_applied,
    ]
    for test in tests:
        test()
        print(f"EDITORIAL_DISCOVERY_V4_PASS {test.__name__}")
    print("HERMES_ALIVE_EDITORIAL_DISCOVERY_V4_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
