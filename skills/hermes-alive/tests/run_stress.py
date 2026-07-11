#!/usr/bin/env python3
from __future__ import annotations

# Marker: HERMES_ALIVE_STRESS_SUITE_V1

import asyncio
import importlib.util
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import MethodType, SimpleNamespace
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
HOOKS = SKILL / "hooks"
SCRIPTS = SKILL / "scripts"
SHARED = Path(tempfile.mkdtemp(prefix="hermes-alive-stress-shared-"))
os.environ["HERMES_ALIVE_SHARED_DIR"] = str(SHARED)
os.environ["HERMES_HOOK_DIR"] = str(HOOKS)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = "true"
os.environ["HERMES_PROACTIVE_WEIXIN_CHAT_ID"] = "fake-stress-chat"
os.environ["VOICE_ENABLED"] = "false"
os.environ["COOLDOWN_ENABLED"] = "false"
os.environ["HERMES_PROACTIVE_DISCOVERY_ENABLED"] = "false"
sys.path.insert(0, str(HOOKS))
sys.path.insert(0, str(HERE))

import interest_learning as interest_module
from content_delivery import ContentDeliveryEngine, DeliveryPayload
from interruption_policy import InterruptionPolicy
from interest_learning import InterestLearningEngine, normalize_item
from proactive_watcher import ProactivePlatformWatcher
from safe_io import append_jsonl, locked_read_json, locked_write_json
from fakes import FakeAdapter

SCALE = float(os.getenv("HERMES_ALIVE_STRESS_SCALE", "1.0"))
SCALE = max(0.01, min(1.0, SCALE))


def scaled(value: int, minimum: int = 1) -> int:
    return max(minimum, int(round(value * SCALE)))


def fd_count() -> int:
    path = Path("/proc/self/fd")
    return len(list(path.iterdir())) if path.is_dir() else -1


def current_metrics() -> dict[str, Any]:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return {
        "fd": fd_count(),
        "threads": threading.active_count(),
        "maxrss_kib": int(usage.ru_maxrss),
    }


class StressRunner:
    def __init__(self) -> None:
        self.groups: list[dict[str, Any]] = []

    def run(self, name: str, func: Callable[[], dict[str, Any]]) -> None:
        before = current_metrics()
        started = time.perf_counter()
        result = func()
        elapsed = time.perf_counter() - started
        after = current_metrics()
        record = {
            "name": name,
            "elapsed_seconds": round(elapsed, 4),
            "before": before,
            "after": after,
            "fd_delta": after["fd"] - before["fd"] if before["fd"] >= 0 else 0,
            "thread_delta": after["threads"] - before["threads"],
            "result": result,
        }
        assert record["fd_delta"] <= 8, record
        assert record["thread_delta"] <= 4, record
        self.groups.append(record)
        print("STRESS_GROUP_PASS", name, json.dumps(record, ensure_ascii=False, sort_keys=True))


def safe_io_stress() -> dict[str, Any]:
    root = SHARED / "safe-io"
    root.mkdir(parents=True, exist_ok=True)
    state = root / "state.json"
    log = root / "events.jsonl"
    workers = scaled(32, 2)
    operations = scaled(250, 10)

    def worker(index: int) -> None:
        for step in range(operations):
            if step % 2:
                append_jsonl(log, {"worker": index, "step": step}, "stress-jsonl.lock")
            else:
                locked_write_json(state, {"worker": index, "step": step}, "stress-json.lock")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(worker, range(workers)))

    lines = log.read_text(encoding="utf-8").splitlines()
    records = [json.loads(line) for line in lines]
    expected = workers * (operations // 2)
    if operations % 2:
        expected += 0
    assert len(records) == expected, (len(records), expected)
    assert isinstance(locked_read_json(state, {}, "stress-json.lock"), dict)
    return {"workers": workers, "operations_per_worker": operations, "jsonl_records": len(records)}


def interest_stress() -> dict[str, Any]:
    base = SHARED / "interest"
    engine = InterestLearningEngine(base)
    memory = {"profile": engine.read_profile(), "logs": {}}

    def read_profile() -> dict[str, Any]:
        return json.loads(json.dumps(memory["profile"]))

    def write_profile(profile: dict[str, Any]) -> None:
        profile = json.loads(json.dumps(profile))
        profile["processed_feedback_keys"] = profile.get("processed_feedback_keys", [])[-300:]
        profile["processed_implicit_keys"] = profile.get("processed_implicit_keys", [])[-300:]
        memory["profile"] = profile

    engine.read_profile = read_profile  # type: ignore[assignment]
    engine.write_profile = write_profile  # type: ignore[assignment]

    real_append = interest_module._append_bounded_jsonl
    def memory_append(path, record, lock_name, max_lines):
        bucket = memory["logs"].setdefault(str(path), [])
        bucket.append(json.loads(json.dumps(record)))
        del bucket[:-max_lines]
    interest_module._append_bounded_jsonl = memory_append
    deliveries = scaled(6000, 100)
    feedback_attempts = scaled(4000, 100)
    try:
        last = None
        for index in range(deliveries):
            last = engine.record_delivery({
                "id": f"item-{index}",
                "title": f"Smoke research {index}",
                "url": f"https://example.invalid/{index}",
                "source": "stress",
                "content_type": "paper",
                "tags": ["smoke", "research"],
            }, tick_id=f"tick-{index}")
        assert last is not None
        applied = 0
        for index in range(feedback_attempts):
            if engine.record_feedback("这篇不错", target_item=last, message_key=f"feedback-{index}") is not None:
                applied += 1
        profile = engine.read_profile()
        assert len(profile["processed_feedback_keys"]) <= 300
        assert all(len(records) <= limit for records, limit in [
            (memory["logs"].get(str(engine.content_seen_path), []), 5000),
            (memory["logs"].get(str(engine.content_items_path), []), 5000),
            (memory["logs"].get(str(engine.feedback_log_path), []), 3000),
        ])
        return {"deliveries": deliveries, "feedback_attempts": feedback_attempts, "feedback_applied": applied, "processed_keys": len(profile["processed_feedback_keys"]), "persistence_mode": "bounded_in_memory_injection"}
    finally:
        interest_module._append_bounded_jsonl = real_append


def delivery_planning_stress() -> dict[str, Any]:
    engine = ContentDeliveryEngine(allowed_file_roots=[SHARED])
    context = {"external": [{"id": f"item-{i}", "title": f"Smoke research item {i}", "url": f"https://example.invalid/{i}", "image_url": f"https://img.example.invalid/{i}.jpg", "source": "stress"} for i in range(12)]}
    count = scaled(10000, 100)
    rich = 0
    for index in range(count):
        item_id = f"item-{index % 12}"
        plan = engine.plan([("research_ping", f"Smoke research item {index % 12}", "fake-provider/fake-model")], context, {"allow_content_share": True, "max_bubbles": 2}, content_ref=item_id)
        assert plan.evidence_score == 1000
        rich += int(plan.rich_payload is not None)
    return {"plans": count, "rich_plans": rich}


def delivery_send_stress() -> dict[str, Any]:
    async def run() -> dict[str, Any]:
        engine = ContentDeliveryEngine(allowed_file_roots=[SHARED])
        adapter = FakeAdapter(fail_text_every=7, raise_text_every=19)
        count = scaled(2000, 100)
        success = 0
        failure = 0
        for index in range(count):
            outcome = await engine.send_text(adapter, "fake-chat", f"message-{index}", metadata={"resolved_model": "fake-provider/fake-model", "is_system": False})
            if outcome.success:
                success += 1
            else:
                failure += 1
        assert success + failure == count
        assert failure > 0
        return {"sends": count, "success": success, "failure": failure}
    return asyncio.run(run())


def policy_stress() -> dict[str, Any]:
    policy = InterruptionPolicy(state_engine=None)
    count = scaled(10000, 200)
    levels = {0: 0, 1: 0, 2: 0, 3: 0}
    for index in range(count):
        mode = index % 6
        state = {"ignored_proactive_count": 0, "mood": {"energy": 50, "annoyance": 0, "pressure": 0}, "current_context": {"flow": "idle", "focus_lock": False}}
        kwargs: dict[str, Any] = {}
        if mode == 0:
            state["current_context"] = {"flow": "debug_flow", "focus_lock": True}
        elif mode == 1:
            state["current_context"] = {"flow": "research_flow", "focus_lock": False}
        elif mode == 2:
            state["ignored_proactive_count"] = 4
        elif mode == 3:
            kwargs["user_active"] = True
        elif mode == 4:
            kwargs.update({"cooldown_allowed": False, "cooldown_reason": "quiet_hours"})
        else:
            state["mood"]["energy"] = 20
        decision = policy.evaluate(state=state, **kwargs)
        levels[decision["level"]] += 1
    assert sum(levels.values()) == count
    return {"evaluations": count, "levels": levels}


def watcher_stress() -> dict[str, Any]:
    async def run() -> dict[str, Any]:
        adapter = FakeAdapter(fail_text_every=11)
        watcher = ProactivePlatformWatcher({"weixin": adapter}, SimpleNamespace())
        watcher._process_control_queue = MethodType(lambda self, adapter, chat_id, tick_id: asyncio.sleep(0, result=False), watcher)
        watcher._voice_state = MethodType(lambda self: None, watcher)
        watcher._user_active_recently = MethodType(lambda self: False, watcher)
        watcher._evaluate_interruption_policy = MethodType(lambda self, **kwargs: {"allow_send": True, "allow_when_user_active": False, "allow_new_topic": True, "allow_content_share": False, "allow_emoji": True, "max_bubbles": 1, "level": 2, "mode": "proactive", "preferred_speech_acts": ["self_talk"], "reason": ["stress"], "skip_reason": None}, watcher)
        watcher._cooldown = MethodType(lambda self: None, watcher)
        watcher._check_discovery = MethodType(lambda self: asyncio.sleep(0, result=None), watcher)
        watcher._check_dream = MethodType(lambda self: asyncio.sleep(0, result=None), watcher)
        watcher._compose_message = MethodType(lambda self, voice, discovery_context, policy_decision=None: asyncio.sleep(0, result=[("self_talk", "stress tick", "fake-provider/fake-model")]), watcher)
        watcher._log = MethodType(lambda self, decision, **extra: None, watcher)
        watcher._log_compose = MethodType(lambda self, *args, **kwargs: None, watcher)
        evidence = {"count": 0}
        watcher._record_interest_delivery = MethodType(lambda self, *args, **kwargs: evidence.__setitem__("count", evidence["count"] + 1), watcher)
        count = scaled(2000, 100)
        sent = 0
        for _ in range(count):
            sent += int(await watcher.tick())
        expected_failures = count // 11
        assert sent == count - expected_failures, (sent, count, expected_failures)
        assert evidence["count"] == sent
        return {"ticks": count, "sent": sent, "failed": expected_failures, "delivery_evidence_records": evidence["count"]}
    return asyncio.run(run())


def lifecycle_cmd(home: Path, source: Path, action: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["HERMES_ALIVE_SHARED_DIR"] = str(home / "hermes_alive_shared")
    args = [sys.executable, str(source / "scripts" / "hermes-alive-lifecycle.py"), action, "--hermes-home", str(home)]
    if action == "install":
        args += ["--source-root", str(source)]
    return subprocess.run(args, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)


def lifecycle_stress() -> dict[str, Any]:
    cycles = scaled(20, 2)
    passed = 0
    for index in range(cycles):
        home = Path(tempfile.mkdtemp(prefix=f"lifecycle-stress-{index}-"))
        for action in ("install", "install", "uninstall", "install", "purge"):
            result = lifecycle_cmd(home, SKILL, action)
            assert result.returncode == 0, (action, result.stdout)
        assert not (home / "skills" / "hermes" / "hermes-alive").exists()
        assert not (home / "hooks" / "hermes-alive").exists()
        assert not (home / "hermes_alive_shared").exists()
        passed += 1
    return {"cycles": cycles, "passed": passed, "operations_per_cycle": 5}


def failure_injection_stress() -> dict[str, Any]:
    path = SCRIPTS / "hermes-alive-lifecycle.py"
    spec = importlib.util.spec_from_file_location("hermes_alive_lifecycle_stress", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    recoveries = 0
    attempts = scaled(50, 5)
    for index in range(attempts):
        base = Path(tempfile.mkdtemp(prefix="swap-injection-"))
        target = base / "target"
        stage = base / "stage"
        rollback = base / "rollback"
        target.mkdir(); stage.mkdir()
        (target / "v").write_text("old", encoding="utf-8")
        (stage / "v").write_text("new", encoding="utf-8")
        real = module.os.replace
        calls = {"count": 0}
        def injected(src, dst):
            calls["count"] += 1
            if calls["count"] == 2:
                raise OSError("injected")
            return real(src, dst)
        module.os.replace = injected
        try:
            try:
                module._swap_directory(stage, target, rollback)
            except OSError:
                pass
            assert (target / "v").read_text(encoding="utf-8") == "old"
            recoveries += 1
        finally:
            module.os.replace = real
    return {"injected_failures": attempts, "recoveries": recoveries}


def result_files() -> dict[str, Any]:
    records = {}
    for path in sorted(SHARED.rglob("*")):
        if path.is_file():
            records[str(path.relative_to(SHARED))] = {"bytes": path.stat().st_size, "lines": len(path.read_text(encoding="utf-8", errors="ignore").splitlines()) if path.suffix in {".jsonl", ".json"} else None}
    return records


def main() -> int:
    tracemalloc.start()
    runner = StressRunner()
    runner.run("safe_io", safe_io_stress)
    runner.run("interest_learning", interest_stress)
    runner.run("delivery_planning", delivery_planning_stress)
    runner.run("delivery_send", delivery_send_stress)
    runner.run("policy", policy_stress)
    runner.run("watcher", watcher_stress)
    runner.run("lifecycle", lifecycle_stress)
    runner.run("failure_injection", failure_injection_stress)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    report = {
        "scale": SCALE,
        "groups": runner.groups,
        "tracemalloc_current_bytes": current,
        "tracemalloc_peak_bytes": peak,
        "tracemalloc_peak_limit_bytes": 160 * 1024 * 1024,
        "resource_files": result_files(),
        "final_metrics": current_metrics(),
    }
    assert peak <= report["tracemalloc_peak_limit_bytes"], report
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("HERMES_ALIVE_STRESS_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
