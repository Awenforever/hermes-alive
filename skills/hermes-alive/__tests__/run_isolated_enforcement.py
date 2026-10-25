#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from types import MethodType, SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
SCRIPTS = ROOT / "scripts"
import sys
for path in (HOOKS, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

RUNTIME = Path(tempfile.mkdtemp(prefix="hermes-alive-isolated-enforcement-"))
os.environ["HERMES_ALIVE_SHARED_DIR"] = str(RUNTIME)
os.environ["HERMES_HOOK_DIR"] = str(HOOKS)
os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = "true"

from isolated_enforcement import (
    MODE_ENV,
    SCOPE_ENV,
    enforcement_gate,
    filter_quality_candidates,
    precompose_enforcement,
    should_override_legacy_quiet,
)
from managed_config import MANAGED_ENV_KEYS
from proactive_quality_governor import ProactiveQualityGovernor, QualityGovernorConfig
from proactive_watcher import ProactivePlatformWatcher
from safe_io import locked_read_json, sha256_text


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class DummyAdapter:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.contents: list[str] = []

    async def send(self, chat_id: str, content: str, metadata: dict[str, Any] | None = None):
        self.contents.append(content)
        return SimpleNamespace(success=not self.fail, error="forced" if self.fail else None)


class FakeCooldown:
    def __init__(self, allowed: bool, reason: str) -> None:
        self.allowed = allowed
        self.reason = reason
        self.recorded: list[str] = []

    def set_mood_cooldown(self, social_urge: float | None) -> None:
        return None

    def can_send(self, msg_type: str):
        return self.allowed, self.reason

    def record_send(self, msg_type: str) -> None:
        self.recorded.append(msg_type)


class FakeGovernor:
    def __init__(self, pre: dict[str, Any], audits: list[dict[str, Any]]) -> None:
        self.pre = pre
        self.audits = audits
        self.commits: list[dict[str, Any]] = []

    def pre_decision(self, *, user_active: bool = False):
        return dict(self.pre)

    def audit_candidate(self, content: str, **kwargs: Any):
        target = sha256_text(content)
        for audit in self.audits:
            if audit.get("message_hash") == target:
                return dict(audit)
        return {
            "would_allow": True,
            "would_reject": False,
            "reasons": [],
            "message_hash": target,
            "affective_candidate": False,
            "silence_episode_id": None,
        }

    def commit_delivery(self, audit: dict[str, Any]) -> bool:
        self.commits.append(dict(audit))
        return True


def enforcement_env(enabled: bool) -> dict[str, str | None]:
    previous = {MODE_ENV: os.environ.get(MODE_ENV), SCOPE_ENV: os.environ.get(SCOPE_ENV)}
    if enabled:
        os.environ[MODE_ENV] = "isolated"
        os.environ[SCOPE_ENV] = "isolated_test"
    else:
        os.environ.pop(MODE_ENV, None)
        os.environ.pop(SCOPE_ENV, None)
    return previous


def restore_env(previous: dict[str, str | None]) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


async def install_stubs(
    watcher: ProactivePlatformWatcher,
    adapter: DummyAdapter,
    *,
    sleep: dict[str, Any] | None = None,
    pre: dict[str, Any] | None = None,
    messages: list[tuple[str, str, str]] | None = None,
    audits: list[dict[str, Any]] | None = None,
    cooldown: Any | None = None,
    control_sent: bool = False,
) -> dict[str, Any]:
    state = {"compose_calls": 0, "circadian_calls": 0}

    async def process_control(self, adapter_obj, chat_id, tick_id):
        return control_sent

    def resolve(self):
        return adapter, "human-peer"

    def circadian(self, *, message_class: str):
        state["circadian_calls"] += 1
        return {
            "enabled": True,
            "mode": "shadow",
            "phase": (sleep or {}).get("phase", "awake"),
            "hard_exempt": False,
        }

    def sleep_decision(self, circadian_decision, *, message_class: str):
        return dict(sleep or {
            "would_allow_dynamic": True,
            "would_block_dynamic": False,
            "dynamic_reason": "awake",
            "phase": "awake",
            "hard_exempt": False,
        })

    def quality_pre(self, *, user_active: bool):
        return dict(pre or {
            "silence_lock": False,
            "recommended_action": "normal_quality_check",
        })

    def voice(self):
        return None

    def inactive(self):
        return False

    def policy(self, **kwargs: Any):
        return None

    def cooldown_fn(self):
        return cooldown

    async def none_async(self, *args: Any, **kwargs: Any):
        return None

    async def compose(self, voice=None, discovery_context=None, policy_decision=None):
        state["compose_calls"] += 1
        return list(messages or [("casual", "允许发送", "test-model")])

    def no_delivery(self):
        return None

    def no_interest(self, *args: Any, **kwargs: Any):
        return False

    watcher._process_control_queue = MethodType(process_control, watcher)
    watcher._resolve_adapter_and_chat_id = MethodType(resolve, watcher)
    watcher._circadian_shadow_decision = MethodType(circadian, watcher)
    watcher._sleep_quiet_policy_shadow_decision = MethodType(sleep_decision, watcher)
    watcher._proactive_quality_shadow_decision = MethodType(quality_pre, watcher)
    watcher._voice_state = MethodType(voice, watcher)
    watcher._user_active_recently = MethodType(inactive, watcher)
    watcher._evaluate_interruption_policy = MethodType(policy, watcher)
    watcher._cooldown = MethodType(cooldown_fn, watcher)
    watcher._check_discovery = MethodType(none_async, watcher)
    watcher._check_dream = MethodType(none_async, watcher)
    watcher._compose_message = MethodType(compose, watcher)
    watcher._content_delivery = MethodType(no_delivery, watcher)
    watcher._record_interest_delivery = MethodType(no_interest, watcher)

    fake = FakeGovernor(pre or {"silence_lock": False}, audits or [])
    watcher._proactive_quality_governor = fake
    return {"state": state, "governor": fake}


def audit(text: str, *, allow: bool, reasons: list[str] | None = None, affective: bool = False, episode: str | None = None) -> dict[str, Any]:
    return {
        "would_allow": allow,
        "would_reject": not allow,
        "reasons": list(reasons or []),
        "message_hash": sha256_text(text),
        "affective_candidate": affective,
        "silence_episode_id": episode,
    }


def test_dual_key_guard() -> None:
    check(enforcement_gate({})["enabled"] is False, "empty environment enabled enforcement")
    check(enforcement_gate({MODE_ENV: "isolated"})["enabled"] is False, "mode alone enabled enforcement")
    check(enforcement_gate({SCOPE_ENV: "isolated_test"})["enabled"] is False, "scope alone enabled enforcement")
    check(enforcement_gate({MODE_ENV: "isolated", SCOPE_ENV: "isolated_test"})["enabled"] is True, "dual key did not enable")
    check(enforcement_gate({MODE_ENV: "live", SCOPE_ENV: "production"})["enabled"] is False, "production-like values enabled")


def test_precompose_sleep_and_silence_blocks() -> None:
    env = {MODE_ENV: "isolated", SCOPE_ENV: "isolated_test"}
    sleep = precompose_enforcement({"would_block_dynamic": True, "hard_exempt": False, "dynamic_reason": "dynamic_sleep_window"}, {"silence_lock": False}, environ=env)
    check(sleep["block"] is True and "dynamic_sleep_window" in sleep["reasons"], "sleep block missing")
    silence = precompose_enforcement({"would_block_dynamic": False}, {"silence_lock": True}, environ=env)
    check(silence["block"] is True and "quality_silence_lock" in silence["reasons"], "silence block missing")
    exempt = precompose_enforcement({"would_block_dynamic": True, "hard_exempt": True}, {"silence_lock": False}, environ=env)
    check(exempt["block"] is False, "hard exemption blocked")


def test_legacy_quiet_override_requires_dynamic_allow() -> None:
    env = {MODE_ENV: "isolated", SCOPE_ENV: "isolated_test"}
    allowed = should_override_legacy_quiet({"would_allow_dynamic": True, "would_block_dynamic": False, "phase": "forced_awake"}, environ=env)
    blocked = should_override_legacy_quiet({"would_allow_dynamic": False, "would_block_dynamic": True}, environ=env)
    check(allowed["override"] is True, "forced-awake override missing")
    check(blocked["override"] is False, "dynamic block incorrectly overrode quiet")


def test_candidate_filter_is_fail_closed_only_when_isolated() -> None:
    messages = [("casual", "一", "m"), ("casual", "二", "m")]
    audits = [audit("一", allow=True)]
    kept, decision = filter_quality_candidates(messages, audits, environ={MODE_ENV: "isolated", SCOPE_ENV: "isolated_test"})
    check([item[1] for item in kept] == ["一"], "missing audit was not rejected")
    check(decision["missing_audit_count"] == 1, "missing audit count wrong")
    unchanged, shadow = filter_quality_candidates(messages, [], environ={})
    check(unchanged == messages and shadow["behavior_changed"] is False, "default shadow behavior changed")


def test_default_shadow_mode_does_not_block() -> None:
    previous = enforcement_env(False)
    try:
        adapter = DummyAdapter()
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        logs: list[tuple[str, dict[str, Any]]] = []
        watcher._log = lambda decision, **extra: logs.append((decision, extra))
        asyncio.run(install_stubs(
            watcher,
            adapter,
            sleep={"would_allow_dynamic": False, "would_block_dynamic": True, "dynamic_reason": "dynamic_sleep_window", "phase": "asleep", "hard_exempt": False},
            pre={"silence_lock": True},
            messages=[("casual", "默认影子仍发送", "m")],
            audits=[audit("默认影子仍发送", allow=False, reasons=["shadow_reject"])],
        ))
        result = asyncio.run(watcher._tick_impl("default-shadow"))
        check(result is True and adapter.contents == ["默认影子仍发送"], "default shadow behavior was enforced")
        check(not any(name.startswith("isolated_enforcement") for name, _ in logs), "isolated logs emitted while disabled")
    finally:
        restore_env(previous)


def test_dynamic_sleep_blocks_before_compose() -> None:
    previous = enforcement_env(True)
    try:
        adapter = DummyAdapter()
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        installed = asyncio.run(install_stubs(
            watcher,
            adapter,
            sleep={"would_allow_dynamic": False, "would_block_dynamic": True, "dynamic_reason": "dynamic_sleep_window", "phase": "asleep", "hard_exempt": False},
        ))
        result = asyncio.run(watcher._tick_impl("sleep-block"))
        check(result is False, "sleep block returned send")
        check(installed["state"]["compose_calls"] == 0 and adapter.contents == [], "composer ran during sleep block")
    finally:
        restore_env(previous)


def test_quality_silence_lock_blocks_before_compose() -> None:
    previous = enforcement_env(True)
    try:
        adapter = DummyAdapter()
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        installed = asyncio.run(install_stubs(watcher, adapter, pre={"silence_lock": True}))
        result = asyncio.run(watcher._tick_impl("silence-block"))
        check(result is False and installed["state"]["compose_calls"] == 0, "silence lock did not block")
    finally:
        restore_env(previous)


def test_control_queue_bypasses_all_social_enforcement() -> None:
    previous = enforcement_env(True)
    try:
        adapter = DummyAdapter()
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        installed = asyncio.run(install_stubs(watcher, adapter, control_sent=True))
        result = asyncio.run(watcher._tick_impl("control"))
        check(result is True, "control queue result wrong")
        check(installed["state"]["circadian_calls"] == 0, "control queue entered social enforcement")
    finally:
        restore_env(previous)


def test_forced_awake_overrides_only_legacy_quiet() -> None:
    previous = enforcement_env(True)
    try:
        adapter = DummyAdapter()
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        asyncio.run(install_stubs(
            watcher,
            adapter,
            sleep={"would_allow_dynamic": True, "would_block_dynamic": False, "dynamic_reason": "user_forced_awake", "phase": "forced_awake", "hard_exempt": False},
            cooldown=FakeCooldown(False, "quiet_hours"),
            messages=[("casual", "被叫醒后回复", "m")],
            audits=[audit("被叫醒后回复", allow=True)],
        ))
        result = asyncio.run(watcher._tick_impl("quiet-override"))
        check(result is True and adapter.contents == ["被叫醒后回复"], "forced awake did not override fixed quiet")

        adapter2 = DummyAdapter()
        watcher2 = ProactivePlatformWatcher({}, SimpleNamespace())
        asyncio.run(install_stubs(
            watcher2,
            adapter2,
            cooldown=FakeCooldown(False, "rate_limit"),
            messages=[("casual", "不应发送", "m")],
            audits=[audit("不应发送", allow=True)],
        ))
        result2 = asyncio.run(watcher2._tick_impl("other-cooldown"))
        check(result2 is False and adapter2.contents == [], "non-quiet cooldown was overridden")
    finally:
        restore_env(previous)


def test_candidate_rejection_filters_mixed_messages() -> None:
    previous = enforcement_env(True)
    try:
        bad = "还没跑完？"
        good = "接下来一周都有雨，出门记得带伞。"
        adapter = DummyAdapter()
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        asyncio.run(install_stubs(
            watcher,
            adapter,
            messages=[("task", bad, "m"), ("weather", good, "m")],
            audits=[
                audit(bad, allow=False, reasons=["task_state_without_fresh_evidence"]),
                audit(good, allow=True),
            ],
        ))
        result = asyncio.run(watcher._tick_impl("mixed-filter"))
        check(result is True and adapter.contents == [good], "candidate filter did not keep only allowed message")
    finally:
        restore_env(previous)


def test_all_candidates_rejected_produces_silence() -> None:
    previous = enforcement_env(True)
    try:
        text = "我在这，你继续"
        adapter = DummyAdapter()
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        asyncio.run(install_stubs(
            watcher,
            adapter,
            messages=[("casual", text, "m")],
            audits=[audit(text, allow=False, reasons=["template_family_cooldown"])],
        ))
        result = asyncio.run(watcher._tick_impl("all-reject"))
        check(result is False and adapter.contents == [], "rejected candidate was sent")
    finally:
        restore_env(previous)


def test_affective_commit_happens_only_after_successful_send() -> None:
    previous = enforcement_env(True)
    try:
        text = "啧"
        accepted = audit(text, allow=True, affective=True, episode="episode-1")
        adapter = DummyAdapter()
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        installed = asyncio.run(install_stubs(watcher, adapter, messages=[("affect", text, "m")], audits=[accepted]))
        check(asyncio.run(watcher._tick_impl("commit-success")) is True, "accepted affect did not send")
        check(len(installed["governor"].commits) == 1, "accepted affect not committed")

        failed_adapter = DummyAdapter(fail=True)
        failed_watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        failed = asyncio.run(install_stubs(failed_watcher, failed_adapter, messages=[("affect", text, "m")], audits=[accepted]))
        check(asyncio.run(failed_watcher._tick_impl("commit-failure")) is False, "failed send reported success")
        check(failed["governor"].commits == [], "failed send committed affect")
    finally:
        restore_env(previous)


def test_real_governor_commit_is_privacy_safe() -> None:
    state_path = RUNTIME / "quality-state.json"
    governor = ProactiveQualityGovernor(
        QualityGovernorConfig(
            enabled=True,
            mode="shadow",
            casual_affect_probability=1.0,
        ),
        state_path=state_path,
    )
    accepted = {
        "would_allow": True,
        "would_reject": False,
        "affective_candidate": True,
        "silence_episode_id": "episode-private-safe",
    }
    check(governor.commit_delivery(accepted) is True, "real commit failed")
    state = locked_read_json(state_path, {}, "proactive_quality_governor_shadow.lock")
    payload = json.dumps(state, ensure_ascii=False)
    check(state.get("affect_spent_episode_id") == "episode-private-safe", "episode not persisted")
    check("PRIVATE_SENTINEL" not in payload, "private sentinel leaked")
    forbidden_keys = {"message", "content", "raw_message", "api_key", "access_token"}
    check(not (forbidden_keys & set(state)), f"private keys leaked: {forbidden_keys & set(state)}")


def test_enforcement_not_exposed_in_managed_config() -> None:
    values = set(MANAGED_ENV_KEYS.values())
    check(MODE_ENV not in values and SCOPE_ENV not in values, "isolated enforcement exposed through managed config")


def test_enforcement_logs_store_no_raw_rejected_message() -> None:
    previous = enforcement_env(True)
    try:
        sentinel = "PRIVATE_SENTINEL_7c9d"
        adapter = DummyAdapter()
        watcher = ProactivePlatformWatcher({}, SimpleNamespace())
        records: list[tuple[str, dict[str, Any]]] = []
        watcher._log = lambda decision, **extra: records.append((decision, extra))
        asyncio.run(install_stubs(
            watcher,
            adapter,
            messages=[("casual", sentinel, "m")],
            audits=[audit(sentinel, allow=False, reasons=["semantic_near_duplicate"])],
        ))
        asyncio.run(watcher._tick_impl("privacy"))
        enforcement_records = [
            {"decision": name, "extra": extra}
            for name, extra in records
            if name.startswith("isolated_enforcement")
        ]
        payload = json.dumps(enforcement_records, ensure_ascii=False)
        check(sentinel not in payload, "raw rejected message leaked into enforcement logs")
    finally:
        restore_env(previous)


def main() -> int:
    tests = [
        test_dual_key_guard,
        test_precompose_sleep_and_silence_blocks,
        test_legacy_quiet_override_requires_dynamic_allow,
        test_candidate_filter_is_fail_closed_only_when_isolated,
        test_default_shadow_mode_does_not_block,
        test_dynamic_sleep_blocks_before_compose,
        test_quality_silence_lock_blocks_before_compose,
        test_control_queue_bypasses_all_social_enforcement,
        test_forced_awake_overrides_only_legacy_quiet,
        test_candidate_rejection_filters_mixed_messages,
        test_all_candidates_rejected_produces_silence,
        test_affective_commit_happens_only_after_successful_send,
        test_real_governor_commit_is_privacy_safe,
        test_enforcement_not_exposed_in_managed_config,
        test_enforcement_logs_store_no_raw_rejected_message,
    ]
    failures: list[str] = []
    for test in tests:
        try:
            test()
            print(f"ISOLATED_ENFORCEMENT_PASS {test.__name__}")
        except Exception as exc:
            failure = f"{test.__name__}:{type(exc).__name__}:{exc}"
            failures.append(failure)
            print(f"ISOLATED_ENFORCEMENT_FAIL {failure}")
    print(json.dumps({"tests": len(tests), "failures": failures}, ensure_ascii=False))
    if failures:
        print("HERMES_ALIVE_ISOLATED_ENFORCEMENT_RESULT=FAIL")
        return 1
    print("HERMES_ALIVE_ISOLATED_ENFORCEMENT_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
