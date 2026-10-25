from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def fresh_modules(base: Path):
    os.environ["HERMES_ALIVE_SHARED_DIR"] = str(base)
    for name in ("topic_dedup", "interest_learning", "discovery"):
        sys.modules.pop(name, None)
    topic = importlib.import_module("topic_dedup")
    interest = importlib.import_module("interest_learning")
    discovery = importlib.import_module("discovery")
    return topic, interest, discovery


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="alive-topic-dedup-") as tmp:
        base = Path(tmp)
        topic, interest, discovery = fresh_modules(base)

        variants = [
            "http://OpenAI.com/index/example/",
            "https://openai.com/index/example#fragment",
            "https://openai.com//index/example/?utm_source=test&fbclid=x",
        ]
        canonical = {topic.canonicalize_url(value) for value in variants}
        require(len(canonical) == 1, f"canonical variants diverged: {canonical}")

        percent_variants = {
            topic.canonicalize_url(
                "https://Example.com/%7euser/report?b=2&a=hello%20world"
            ),
            topic.canonicalize_url(
                "http://example.com:80/~user/report?a=hello+world&b=2"
            ),
        }
        require(
            len(percent_variants) == 1,
            f"percent-encoding variants diverged: {percent_variants}",
        )
        unicode_path_variants = {
            topic.canonicalize_url("https://example.com/烟雾/报告"),
            topic.canonicalize_url(
                "https://example.com/%E7%83%9F%E9%9B%BE/%E6%8A%A5%E5%91%8A"
            ),
        }
        require(
            len(unicode_path_variants) == 1,
            f"Unicode path variants diverged: {unicode_path_variants}",
        )
        ipv6_variants = {
            topic.canonicalize_url("http://[2001:DB8::1]:80/a//b?gclid=x"),
            topic.canonicalize_url("https://[2001:db8::1]:443/a/b"),
        }
        require(
            ipv6_variants == {"https://[2001:db8::1]/a/b"},
            f"IPv6 canonicalization invalid: {ipv6_variants}",
        )

        item = {
            "id": "source-id-1",
            "source": "OpenAI",
            "title": "OpenAI and Hugging Face address security incident",
            "summary": "Initial incident report",
            "url": variants[0],
        }
        rewritten = {
            **item,
            "id": "source-id-2",
            "title": "两家公司公开了一次模型评估安全事件处理过程",
            "url": variants[1],
        }

        store = topic.TopicDedupStore(
            base,
            cooldown_hours=24,
            reservation_ttl_seconds=120,
        )
        first = store.reserve(item, tick_id="tick-one")
        require(first.allowed and first.reservation_id, "first reservation rejected")
        second = store.reserve(rewritten, tick_id="tick-two")
        require(
            second.blocked and second.reason == "topic_reserved_by_another_tick",
            f"concurrent duplicate not blocked: {second.to_dict()}",
        )
        valid = store.validate_reservation(
            item,
            reservation_id=first.reservation_id,
        )
        require(valid.allowed, "own reservation became invalid")
        store.commit_delivery(
            item,
            tick_id="tick-one",
            reservation_id=first.reservation_id,
            now=1_000_000,
        )
        repeat = store.check(rewritten, now=1_000_100)
        require(
            repeat.blocked and repeat.reason == "topic_delivered_within_cooldown",
            f"rewritten same URL bypassed cooldown: {repeat.to_dict()}",
        )
        expired = store.check(rewritten, now=1_000_000 + 24 * 3600 + 1)
        require(expired.allowed, "24h cooldown boundary did not reopen")

        failed = store.reserve(
            {"title": "A distinct delivery that fails", "url": "https://example.org/fail"},
            tick_id="failed-send",
            now=2_000_000,
        )
        require(failed.allowed, "failed-send reservation rejected")
        store.release(reservation_id=failed.reservation_id)
        retry = store.reserve(
            {"title": "A distinct delivery that fails", "url": "https://example.org/fail"},
            tick_id="retry-send",
            now=2_000_001,
        )
        require(retry.allowed, "released failed send remained blocked")
        store.release(reservation_id=retry.reservation_id)

        original_update = {
            "title": "Material update test",
            "summary": "version one",
            "url": "https://example.org/update",
        }
        store.commit_delivery(original_update, tick_id="u1", now=3_000_000)
        changed_update = {
            **original_update,
            "summary": "version two with confirmed new evidence",
            "material_update": True,
            "update_token": "v2",
        }
        update_decision = store.check(changed_update, now=3_000_100)
        require(
            update_decision.allowed and update_decision.reason == "material_update_allowed",
            f"material update rejected: {update_decision.to_dict()}",
        )

        title_a = {
            "source": "feed-a",
            "title": "Same event title from multiple feeds",
            "summary": "a",
        }
        title_b = {
            "source": "feed-b",
            "title": "Same event title from multiple feeds",
            "summary": "b",
        }
        store.commit_delivery(title_a, tick_id="title-one", now=4_000_000)
        title_repeat = store.check(title_b, now=4_000_010)
        require(title_repeat.blocked, "same no-URL topic from another feed was allowed")

        concurrency_item = {
            "title": "Concurrent tick item",
            "url": "https://example.org/concurrent?utm_source=a",
        }
        concurrent_store = topic.TopicDedupStore(base / "concurrency")

        def reserve(index: int):
            return concurrent_store.reserve(concurrency_item, tick_id=f"c-{index}")

        with ThreadPoolExecutor(max_workers=8) as executor:
            decisions = list(executor.map(reserve, range(8)))
        require(sum(decision.allowed for decision in decisions) == 1, "concurrent reservations allowed more than one tick")

        normalized_a = interest.normalize_item(item)
        normalized_b = interest.normalize_item(rewritten)
        require(
            normalized_a["content_identity"] == normalized_b["content_identity"],
            "canonical variants produced different interest-learning IDs",
        )
        require(
            normalized_a["topic_unit_id"] == normalized_b["topic_unit_id"],
            "text and link were not one topic unit",
        )

        discovery_base = base / "discovery"
        os.environ["HERMES_ALIVE_SHARED_DIR"] = str(discovery_base)
        sys.modules.pop("topic_dedup", None)
        sys.modules.pop("interest_learning", None)
        sys.modules.pop("discovery", None)
        topic2 = importlib.import_module("topic_dedup")
        discovery2 = importlib.import_module("discovery")
        dstore = topic2.TopicDedupStore(discovery_base)
        dstore.commit_delivery(item, tick_id="d1")
        engine = discovery2.DiscoveryEngine()
        filtered = engine._dedup([rewritten, {"title": "new item", "url": "https://example.org/new"}])
        require(len(filtered) == 1, f"discovery persistent filter failed: {filtered}")

        rotation_base = base / "cached-rotation"
        os.environ["HERMES_ALIVE_SHARED_DIR"] = str(rotation_base)
        sys.modules.pop("topic_dedup", None)
        sys.modules.pop("interest_learning", None)
        sys.modules.pop("discovery", None)
        topic3 = importlib.import_module("topic_dedup")
        discovery3 = importlib.import_module("discovery")
        rotation_items = [
            {
                "id": f"rotation-{index}",
                "source": "fixture",
                "title": f"Interesting cached post {index}",
                "summary": f"Distinct cached summary {index}",
                "url": f"https://example.org/cached/{index}",
                "score": 0.9 - index * 0.05,
            }
            for index in range(1, 5)
        ]
        rotation_engine = discovery3.DiscoveryEngine()
        rotation_engine._cached = {
            "external": [dict(value) for value in rotation_items],
            "local": [],
            "fetched_at": "fixture",
        }
        first_view = rotation_engine.get_recent()
        require(
            isinstance(first_view, dict)
            and [value["id"] for value in first_view["external"]]
            == [value["id"] for value in rotation_items],
            f"initial cached candidate order changed: {first_view}",
        )
        require(
            len(rotation_engine._cached["external"]) == len(rotation_items),
            "eligible view mutated the complete discovery cache",
        )

        rotation_store = topic3.TopicDedupStore(rotation_base)
        rotation_store.commit_delivery(rotation_items[0], tick_id="rotation-1")
        second_view = rotation_engine.get_recent()
        require(
            [value["id"] for value in second_view["external"]]
            == [value["id"] for value in rotation_items[1:]],
            f"delivered first cached item was not consumed: {second_view}",
        )
        rotation_store.commit_delivery(rotation_items[1], tick_id="rotation-2")
        third_view = rotation_engine.get_recent()
        require(
            [value["id"] for value in third_view["external"]]
            == [value["id"] for value in rotation_items[2:]],
            f"second cached read did not rotate forward: {third_view}",
        )

        restarted_engine = discovery3.DiscoveryEngine()
        restarted_engine._cached = {
            "external": [dict(value) for value in rotation_items],
            "local": [],
            "fetched_at": "fixture-after-restart",
        }
        restarted_view = restarted_engine.get_recent()
        require(
            [value["id"] for value in restarted_view["external"]]
            == [value["id"] for value in rotation_items[2:]],
            f"cached rotation history did not survive engine restart: {restarted_view}",
        )

        rotation_store.commit_delivery(rotation_items[2], tick_id="rotation-3")
        rotation_store.commit_delivery(rotation_items[3], tick_id="rotation-4")
        exhausted = restarted_engine.get_recent()
        require(
            exhausted["external"] == [],
            f"exhausted cache replayed a delivered item: {exhausted}",
        )
        require(
            exhausted["external_cached_count"] == 4
            and exhausted["external_eligible_count"] == 0
            and exhausted["external_suppressed_count"] == 4,
            f"cached rotation counters invalid: {exhausted}",
        )

        updated_first = {
            **rotation_items[0],
            "summary": "Confirmed material update with new evidence",
            "material_update": True,
            "update_token": "rotation-v2",
        }
        restarted_engine._cached = {
            "external": [updated_first, *[dict(value) for value in rotation_items[1:]]],
            "local": [],
            "fetched_at": "fixture-material-update",
        }
        material_view = restarted_engine.get_recent()
        require(
            [value["id"] for value in material_view["external"]]
            == [rotation_items[0]["id"]],
            f"material update did not re-enter exhausted cache: {material_view}",
        )

        state_text = (base / "state/topic_delivery_history.json").read_text(encoding="utf-8")
        require("openai.com" not in state_text.lower(), "raw URL leaked into delivery history")
        require(item["title"] not in state_text, "raw title leaked into delivery history")
        parsed_state = json.loads(state_text)
        require(parsed_state["schema_version"] == 1, "unexpected history schema")

        backup_path = base / "state/topic_delivery_history.json.bak"
        require(backup_path.is_file(), "last-good state backup was not created")
        state_path = base / "state/topic_delivery_history.json"
        original_state = state_path.read_text(encoding="utf-8")
        state_path.write_text('{"truncated":\n', encoding="utf-8")
        recovered = topic.TopicDedupStore(base, cooldown_hours=24)
        recovered_repeat = recovered.check(rewritten, now=1_000_100)
        require(
            recovered_repeat.blocked,
            "truncated primary history bypassed duplicate guard",
        )
        state_path.write_text('{"truncated":\n', encoding="utf-8")
        backup_path.write_text("not-json\n", encoding="utf-8")
        fail_closed = topic.TopicDedupStore(base, cooldown_hours=24)
        fail_closed_decision = fail_closed.check(
            {"title": "new item", "url": "https://example.org/fail-closed"},
            now=1_000_101,
        )
        require(
            fail_closed_decision.blocked
            and fail_closed_decision.reason == "topic_history_unreadable_fail_closed",
            f"double-corrupt history did not fail closed: {fail_closed_decision.to_dict()}",
        )
        state_path.write_text(original_state, encoding="utf-8")

        watcher = (HOOKS / "proactive_watcher.py").read_text(encoding="utf-8")
        for marker in (
            "topic_dedup_reservation",
            "topic_reservation_invalid_before_text_send",
            "topic_reservation_invalid_before_rich_send",
            "topic_dedup_committed",
            "topic_dedup_released",
        ):
            require(marker in watcher, f"watcher integration marker missing: {marker}")

        print("TOPIC_DEDUP_CONTRACTS=PASS")
        print("canonical_url_variants=PASS")
        print("cross_tick_same_url=PASS")
        print("semantic_rephrase_same_url=PASS")
        print("text_link_topic_unit=PASS")
        print("concurrent_tick_atomic_reservation=PASS")
        print("failed_send_release=PASS")
        print("material_update_exception=PASS")
        print("discovery_persistent_filter=PASS")
        print("cached_candidate_rotation=PASS")
        print("delivered_candidate_excluded=PASS")
        print("next_unseen_candidate_selected=PASS")
        print("cache_exhaustion_no_replay=PASS")
        print("rotation_survives_restart=PASS")
        print("material_update_reenters_queue=PASS")
        print("safe_hash_only_history=PASS")
        print("percent_encoding_ipv6=PASS")
        print("corrupt_history_recovery_fail_closed=PASS")
        print("watcher_pre_each_send_guards=PASS")


if __name__ == "__main__":
    main()
