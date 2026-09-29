#!/usr/bin/env python3
"""Regression contracts for diverse, fresh Alive editorial discovery."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from discovery import DiscoveryEngine, ExternalDiscovery, _score_item  # noqa: E402
from proactive_watcher import ProactivePlatformWatcher  # noqa: E402


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


def test_news_aggregator_caps_real_publishers() -> None:
    engine = DiscoveryEngine.__new__(DiscoveryEngine)
    engine._sources_config = {
        "budgets": {"max_per_run": 5, "max_per_source": 1, "max_per_lane": 5},
        "editorial": {"lane_order": ["culture_people"]},
    }
    items = []
    for index, publisher in enumerate(("媒体甲", "媒体乙", "媒体甲")):
        item = candidate("culture_people", index)
        item.update({"source": "news_search", "publisher": publisher})
        items.append(item)
    result = engine._enforce_budget(items)
    check([item["publisher"] for item in result] == ["媒体甲", "媒体乙"], result)


def test_manual_discovery_is_real_content_only() -> None:
    policy = ProactivePlatformWatcher._manual_discovery_policy()
    check(policy["mode"] == "novel_value", policy)
    check(policy["allow_content_share"] is True, policy)
    check("content_ref" in policy["prompt_directives"], policy)
    control_source = (HOOKS / "alive_control.py").read_text(encoding="utf-8")
    check('data["discovery_once"] = True' in control_source, "discover command missing")
    check("Hermes Alive 主动推送测试" not in policy["prompt_directives"], "static test leaked")
    watcher_source = (HOOKS / "proactive_watcher.py").read_text(encoding="utf-8")
    check("await self._wait_for_next_tick()" in watcher_source, "one-shot request is not prompt")


def test_manual_discovery_stays_evidence_bound_after_discovery() -> None:
    reason = ProactivePlatformWatcher._manual_discovery_terminal_reason(
        manual_discovery=True,
        discovery_available=False,
    )
    check(reason == "no_acceptable_evidence_source", reason)
    reason = ProactivePlatformWatcher._manual_discovery_terminal_reason(
        manual_discovery=True,
        discovery_available=True,
    )
    check(reason == "", reason)


def test_manual_discovery_forces_refresh_after_empty_cache() -> None:
    class Config:
        proactive_platform_enabled = True

    class Engine:
        def __init__(self) -> None:
            self.collect_calls = 0

        def should_run(self) -> bool:
            return False

        async def collect(self) -> dict[str, object]:
            self.collect_calls += 1
            return {}

        def has_fresh(self) -> bool:
            return True

        def get_recent(self) -> dict[str, object]:
            return {"external": [{"id": "fresh"}], "local": []}

    watcher = ProactivePlatformWatcher({}, Config())
    watcher._feature_enabled = lambda _name: True
    engine = Engine()
    watcher._discovery_engine = engine
    result = asyncio.run(watcher._check_discovery(force_refresh=True))
    check(engine.collect_calls == 1, str(engine.collect_calls))
    check(result is not None and result["external"][0]["id"] == "fresh", str(result))


def test_unconsumed_candidates_survive_refresh() -> None:
    engine = DiscoveryEngine()
    engine._topic_dedup.filter_candidates = lambda items: (items, [])
    item = {
        "source": "example",
        "lane": "technology",
        "title": "A useful item",
        "url": "https://example.test/item",
    }
    first = engine._dedup([dict(item)])
    second = engine._dedup([dict(item)])
    check(len(first) == 1, str(first))
    check(len(second) == 1, str(second))


def test_configured_queries_drive_source_requests() -> None:
    class Response:
        status = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def text(self) -> str:
            return "<feed xmlns='http://www.w3.org/2005/Atom'></feed>"

        async def json(self) -> dict[str, list]:
            return {"items": []}

    async def exercise() -> None:
        engine = ExternalDiscovery(
            {
                "sources": {
                    "arxiv": {"query": "cat:stat.ML", "max_results": 7},
                    "github": {"query": "topic:robotics stars:>42", "sort": "forks", "per_page": 6},
                }
            }
        )
        urls: list[str] = []

        async def session() -> object:
            return object()

        def request(_session: object, url: str, **_kwargs: object) -> Response:
            urls.append(url)
            return Response()

        engine._get_session = session
        engine._request = request
        await engine._collect_arxiv()
        await engine._collect_github_trending()
        check("cat%3Astat.ML" in urls[0] and "max_results=7" in urls[0], urls[0])
        check("topic%3Arobotics+stars%3A%3E42" in urls[1], urls[1])
        check("sort=forks" in urls[1] and "per_page=6" in urls[1], urls[1])

    asyncio.run(exercise())
    reason = ProactivePlatformWatcher._manual_discovery_terminal_reason(
        manual_discovery=False,
        discovery_available=False,
    )
    check(reason == "", reason)


def main() -> int:
    tests = [
        test_no_academic_source_bonus,
        test_stale_current_affairs_is_rejected,
        test_lanes_are_interleaved_and_capped,
        test_proxy_is_opt_in_and_applied,
        test_news_aggregator_caps_real_publishers,
        test_manual_discovery_is_real_content_only,
        test_manual_discovery_stays_evidence_bound_after_discovery,
        test_manual_discovery_forces_refresh_after_empty_cache,
        test_unconsumed_candidates_survive_refresh,
        test_configured_queries_drive_source_requests,
    ]
    for test in tests:
        test()
        print(f"EDITORIAL_DISCOVERY_V4_PASS {test.__name__}")
    print("HERMES_ALIVE_EDITORIAL_DISCOVERY_V4_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
