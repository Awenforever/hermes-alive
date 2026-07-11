#!/usr/bin/env python3
from __future__ import annotations

# Marker: HERMES_ALIVE_MATRIX_SUITE_V1
# Marker: HERMES_ALIVE_MATRIX_MANAGED_ENV_PRECEDENCE_FIX_V2
# Marker: HERMES_ALIVE_TEST_SECRET_SENTINEL_FIX_V3

import argparse
import asyncio
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
HOOKS = SKILL / "hooks"
SCRIPTS = SKILL / "scripts"
SHARED = Path(tempfile.mkdtemp(prefix="hermes-alive-matrix-shared-"))
os.environ["HERMES_ALIVE_SHARED_DIR"] = str(SHARED)
os.environ["HERMES_HOOK_DIR"] = str(HOOKS)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.path.insert(0, str(HOOKS))
sys.path.insert(0, str(HERE))

from alive_state import AliveStateEngine
from content_delivery import ContentDeliveryEngine, DeliveryPayload
from interruption_policy import InterruptionPolicy
from interest_learning import InterestLearningEngine
from llm_message_composer import LLMMessageComposer
from managed_config import load_managed_env, managed_config_path
from proactive_watcher import ProactivePlatformWatcher
from fakes import FakeAdapter


@dataclass
class CaseResult:
    name: str
    passed: bool
    elapsed_ms: float
    detail: str = ""


class Runner:
    def __init__(self) -> None:
        self.results: list[CaseResult] = []

    def run(self, name: str, func: Callable[[], Any]) -> None:
        import time
        started = time.perf_counter()
        try:
            value = func()
            if asyncio.iscoroutine(value):
                asyncio.run(value)
            self.results.append(CaseResult(name, True, (time.perf_counter() - started) * 1000))
            print(f"MATRIX_PASS {name}")
        except Exception:
            detail = traceback.format_exc()
            self.results.append(CaseResult(name, False, (time.perf_counter() - started) * 1000, detail))
            print(f"MATRIX_FAIL {name}\n{detail}")

    def finish(self) -> int:
        report = {
            "total": len(self.results),
            "passed": sum(item.passed for item in self.results),
            "failed": sum(not item.passed for item in self.results),
            "results": [item.__dict__ for item in self.results],
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if report["failed"]:
            print("HERMES_ALIVE_MATRIX_RESULT=FAIL")
            return 1
        print("HERMES_ALIVE_MATRIX_RESULT=PASS")
        return 0


def assert_true(value: Any, message: str = "assertion failed") -> None:
    if not value:
        raise AssertionError(message)


def lifecycle_cmd(home: Path, *args: str, source: Path | None = None) -> subprocess.CompletedProcess[str]:
    lifecycle = (source or SKILL) / "scripts" / "hermes-alive-lifecycle.py"
    env = dict(os.environ)
    env.update({
        "HOME": str(home),
        "HERMES_HOME": str(home),
        "HERMES_ALIVE_SHARED_DIR": str(home / "hermes_alive_shared"),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    return subprocess.run(
        [sys.executable, str(lifecycle), *args, "--hermes-home", str(home)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        check=False,
    )


def provider_missing() -> None:
    home = Path(tempfile.mkdtemp(prefix="provider-missing-"))
    result = lifecycle_cmd(home, "configure", "--provider-check-only")
    assert result.returncode == 2, result.stdout
    assert "HERMES_ALIVE_PROVIDER_SETUP_REQUIRED" in result.stdout
    assert "setup model" in result.stdout


def provider_configured() -> None:
    home = Path(tempfile.mkdtemp(prefix="provider-ready-"))
    (home / "config.yaml").write_text("model: fake-provider/fake-model\n", encoding="utf-8")
    result = lifecycle_cmd(home, "configure", "--provider-check-only")
    assert result.returncode == 0, result.stdout
    assert "HERMES_ALIVE_PROVIDER_READY" in result.stdout
    assert '"model": "fake-provider/fake-model"' in result.stdout


def provider_malformed() -> None:
    home = Path(tempfile.mkdtemp(prefix="provider-bad-"))
    (home / "config.yaml").write_text("model: [unterminated\n", encoding="utf-8")
    result = lifecycle_cmd(home, "configure", "--provider-check-only")
    assert result.returncode == 2, result.stdout
    assert "config_parse_failed" in result.stdout


def managed_absent() -> None:
    old = os.environ.pop("HERMES_PROACTIVE_PLATFORM_ENABLED", None)
    try:
        path = managed_config_path()
        path.unlink(missing_ok=True)
        assert load_managed_env() == {}
    finally:
        if old is not None:
            os.environ["HERMES_PROACTIVE_PLATFORM_ENABLED"] = old


def managed_valid_and_override() -> None:
    path = managed_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "values": {
                    "enabled": True,
                    "timezone": "Asia/Singapore",
                    "emoji_policy": "contextual",
                }
            }
        ),
        encoding="utf-8",
    )

    names = (
        "HERMES_PROACTIVE_PLATFORM_ENABLED",
        "TZ",
        "HERMES_ALIVE_EMOJI_POLICY",
    )
    previous = {
        name: os.environ.get(name)
        for name in names
    }

    try:
        # A missing environment value is loaded from managed configuration.
        os.environ.pop(
            "HERMES_PROACTIVE_PLATFORM_ENABLED",
            None,
        )
        os.environ.pop(
            "HERMES_ALIVE_EMOJI_POLICY",
            None,
        )

        # An explicit environment value wins when overwrite=False.
        os.environ["TZ"] = "Existing/Zone"

        loaded = load_managed_env(
            overwrite=False
        )

        assert (
            os.environ[
                "HERMES_PROACTIVE_PLATFORM_ENABLED"
            ]
            == "true"
        )
        assert os.environ["TZ"] == "Existing/Zone"
        assert (
            os.environ[
                "HERMES_ALIVE_EMOJI_POLICY"
            ]
            == "contextual"
        )
        assert (
            loaded[
                "HERMES_PROACTIVE_PLATFORM_ENABLED"
            ]
            == "true"
        )
        assert (
            loaded["HERMES_ALIVE_EMOJI_POLICY"]
            == "contextual"
        )
        assert "TZ" not in loaded

        # overwrite=True is an explicit test/tooling operation.
        loaded = load_managed_env(
            overwrite=True
        )
        assert loaded["TZ"] == "Asia/Singapore"
        assert os.environ["TZ"] == "Asia/Singapore"
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def managed_corrupt() -> None:
    path = managed_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{bad json", encoding="utf-8")
    assert load_managed_env(overwrite=True) == {}


def policy_matrix() -> None:
    policy = InterruptionPolicy(state_engine=None)
    base = {"ignored_proactive_count": 0, "mood": {"energy": 50, "annoyance": 0, "pressure": 0}, "current_context": {"flow": "idle", "focus_lock": False}}
    rows = [
        ("debug", {**base, "current_context": {"flow": "debug_flow", "focus_lock": True}, "mood": {"energy": 50, "annoyance": 0, "pressure": 80}}, {}, {"level": 1, "allow_content_share": False, "max_bubbles": 1}),
        ("research", {**base, "current_context": {"flow": "research_flow", "focus_lock": False}}, {}, {"level": 2, "allow_content_share": True, "max_bubbles": 2}),
        ("user_active", base, {"user_active": True}, {"level": 0, "allow_send": False, "skip_reason": "user_active"}),
        ("ignored", {**base, "ignored_proactive_count": 4}, {}, {"level": 3, "allow_content_share": False}),
        ("night", {**base, "current_context": {"flow": "night_mode", "focus_lock": False}}, {}, {"level": 1, "max_bubbles": 1}),
        ("low_energy", {**base, "mood": {"energy": 20, "annoyance": 0, "pressure": 0}}, {}, {"level": 1, "allow_new_topic": False}),
        ("casual", {**base, "current_context": {"flow": "casual_flow", "focus_lock": False}}, {}, {"level": 2, "max_bubbles": 3}),
        ("quiet", base, {"cooldown_allowed": False, "cooldown_reason": "quiet_hours"}, {"level": 0, "allow_send": False, "skip_reason": "quiet_hours"}),
    ]
    for name, state, kwargs, expected in rows:
        decision = policy.evaluate(state=state, **kwargs)
        for key, value in expected.items():
            assert decision[key] == value, (name, key, decision)
        assert decision["allow_emoji"] is True
        assert "numeric" not in decision["prompt_directives"].lower()


def delivery_plans() -> None:
    engine = ContentDeliveryEngine(allowed_file_roots=[SHARED], max_file_bytes=1024)
    context = {"external": [
        {"id": "img", "title": "Smoke paper", "url": "https://example.invalid/paper", "image_url": "//img.example.invalid/a.jpg", "source": "example"},
        {"id": "bad", "title": "Bad URL", "url": "file:///etc/passwd", "source": "example"},
    ]}
    messages = [("research_ping", "Smoke paper", "fake-provider/fake-model")]
    exact = engine.plan(messages, context, {"allow_content_share": True, "max_bubbles": 2}, content_ref="img")
    assert exact.evidence_score == 1000
    assert exact.rich_payload and exact.rich_payload.kind == "image"
    assert exact.rich_payload.image_url.startswith("https://")
    unknown = engine.plan(messages, context, {"allow_content_share": True, "max_bubbles": 3}, content_ref="missing")
    assert unknown.rich_payload is None and unknown.evidence_score == 0
    blocked = engine.plan(messages, context, {"allow_content_share": False, "max_bubbles": 1}, content_ref="img")
    assert blocked.rich_payload is None and len(blocked.text_messages) == 1
    invalid = engine.plan([("content_share", "Bad URL", "hermes")], context, {"allow_content_share": True, "max_bubbles": 2}, content_ref="bad")
    assert invalid.rich_payload is None


async def delivery_send_matrix() -> None:
    root = SHARED / "files"
    root.mkdir(parents=True, exist_ok=True)
    small = root / "small.txt"
    small.write_text("ok", encoding="utf-8")
    large = root / "large.bin"
    large.write_bytes(b"x" * 2048)
    engine = ContentDeliveryEngine(allowed_file_roots=[root], max_file_bytes=1024)
    metadata = {"resolved_model": "fake-provider/fake-model", "is_system": False}

    adapter = FakeAdapter()
    text = await engine.send_text(adapter, "chat", "hello", metadata=metadata)
    assert text.success and adapter.calls[-1]["metadata"] == metadata

    image = await engine.send_rich(adapter, "chat", DeliveryPayload(kind="image", image_url="https://example.invalid/a.jpg", url="https://example.invalid/a", text="caption"), metadata={"resolved_model": "hermes", "is_system": True})
    assert image.success and image.mode == "native_image"

    fallback_adapter = FakeAdapter(fail_image_every=1)
    fallback = await engine.send_rich(fallback_adapter, "chat", DeliveryPayload(kind="image", image_url="https://example.invalid/a.jpg", url="https://example.invalid/a", text="caption"), metadata={"resolved_model": "hermes"})
    assert fallback.success and fallback.fallback_used
    assert [call["kind"] for call in fallback_adapter.calls] == ["image", "text"]

    allowed = await engine.send_rich(adapter, "chat", DeliveryPayload(kind="file", file_path=str(small), title="small"), metadata={"resolved_model": "hermes"})
    assert allowed.success and allowed.mode == "native_file"
    outside = await engine.send_rich(adapter, "chat", DeliveryPayload(kind="file", file_path="/etc/passwd", title="bad"), metadata={"resolved_model": "hermes"})
    assert not outside.success
    oversized = await engine.send_rich(adapter, "chat", DeliveryPayload(kind="file", file_path=str(large), title="large"), metadata={"resolved_model": "hermes"})
    assert not oversized.success

    raising = FakeAdapter(raise_text_every=1)
    outcome = await engine.send_text(raising, "chat", "fail", metadata=metadata)
    assert not outcome.success and "RuntimeError" in (outcome.error or "")


def content_ref_hidden() -> None:
    composer = object.__new__(LLMMessageComposer)
    discovery = {"external": [{"id": "abc", "title": "x"}]}
    candidate = "hello [[CONTENT_REF:abc]] world"
    ref = composer._extract_content_ref(candidate, discovery)
    cleaned = composer._sanitize(candidate)
    assert ref == "abc"
    assert "CONTENT_REF" not in cleaned
    candidate = "hello [[CONTENT_REF:missing]]"
    ref = composer._extract_content_ref(candidate, discovery)
    cleaned = composer._sanitize(candidate)
    assert ref is None
    assert "CONTENT_REF" not in cleaned
    assert "MEDIA:" not in composer._sanitize("MEDIA:https://example.invalid/a.jpg visible")


def learning_matrix() -> None:
    base = Path(tempfile.mkdtemp(prefix="learning-matrix-"))
    engine = InterestLearningEngine(base)
    item = {"id": "paper-1", "title": "Satellite smoke research", "url": "https://example.invalid/paper-1", "source": "journal", "content_type": "paper", "tags": ["smoke", "research"]}
    delivered = engine.record_delivery(item, tick_id="t1")
    positive = engine.record_feedback("这篇不错", target_item=delivered, message_key="positive-1")
    assert positive and positive["event"] == "explicit_positive"
    assert engine.record_feedback("这篇不错", target_item=delivered, message_key="positive-1") is None
    negative = engine.record_feedback("别再推这类", target_item=delivered, message_key="negative-1")
    assert negative and negative["event"] == "explicit_negative"
    profile = engine.read_profile()
    assert len(profile["processed_feedback_keys"]) == 2

    state = {"last_user_reply_at": None}
    ignored = engine.record_repeated_ignored(3, state=state)
    assert ignored and ignored["event"] == "repeated_ignored"
    assert engine.record_repeated_ignored(4, state=state) is None

    reloaded = InterestLearningEngine(base)
    assert reloaded.was_seen(item)
    preferred = reloaded.rank_item(item, 0.5)
    neutral = reloaded.rank_item({"id": "other", "title": "Unrelated", "source": "other", "content_type": "news", "tags": ["other"]}, 0.5)
    assert preferred["score"] != neutral["score"]


def watcher_metadata_and_reference() -> None:
    watcher = ProactivePlatformWatcher({}, SimpleNamespace())
    model = watcher._metadata("fake-provider/fake-model")
    system = watcher._metadata("hermes")
    assert model["resolved_model"] == "fake-provider/fake-model"
    assert model["is_system"] is False
    assert system["resolved_model"] == "hermes"
    assert system["is_system"] is True
    visible, ref = watcher._extract_content_reference([
        ("content_share", "hello", "fake-provider/fake-model"),
        ("__content_ref__", "abc", "hermes"),
    ])
    assert ref == "abc" and len(visible) == 1


def lifecycle_matrix() -> None:
    home = Path(tempfile.mkdtemp(prefix="lifecycle-matrix-"))
    env = dict(os.environ)
    env["HERMES_ALIVE_SHARED_DIR"] = str(home / "hermes_alive_shared")
    install = lifecycle_cmd(home, "install", "--source-root", str(SKILL))
    assert install.returncode == 0, install.stdout
    second = lifecycle_cmd(home, "install", "--source-root", str(SKILL))
    assert second.returncode == 0, second.stdout
    verify = lifecycle_cmd(home, "verify")
    assert verify.returncode == 0, verify.stdout
    marker = home / "hermes_alive_shared" / "preferences" / "preserve.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("keep", encoding="utf-8")
    un = lifecycle_cmd(home, "uninstall")
    assert un.returncode == 0, un.stdout
    assert marker.is_file()
    assert not (home / "hooks" / "hermes-alive").exists()
    reinstall = lifecycle_cmd(home, "install", "--source-root", str(SKILL))
    assert reinstall.returncode == 0, reinstall.stdout
    purge = lifecycle_cmd(home, "purge")
    assert purge.returncode == 0, purge.stdout
    assert not (home / "hermes_alive_shared").exists()


def lifecycle_compile_failure_preserves_previous() -> None:
    home = Path(tempfile.mkdtemp(prefix="lifecycle-compile-rollback-"))
    old = Path(tempfile.mkdtemp(prefix="source-old-")) / "skill"
    new = Path(tempfile.mkdtemp(prefix="source-bad-")) / "skill"
    shutil.copytree(SKILL, old)
    shutil.copytree(SKILL, new)
    (old / "TEST_VERSION").write_text("old", encoding="utf-8")
    (new / "TEST_VERSION").write_text("new", encoding="utf-8")
    first = lifecycle_cmd(home, "install", "--source-root", str(old), source=old)
    assert first.returncode == 0, first.stdout
    (new / "hooks" / "broken.py").write_text("def broken(:\n", encoding="utf-8")
    failed = lifecycle_cmd(home, "install", "--source-root", str(new), source=new)
    assert failed.returncode != 0
    target = home / "skills" / "hermes" / "hermes-alive"
    assert (target / "TEST_VERSION").read_text(encoding="utf-8") == "old"
    assert lifecycle_cmd(home, "verify").returncode == 0


def load_lifecycle_module():
    path = SCRIPTS / "hermes-alive-lifecycle.py"
    spec = importlib.util.spec_from_file_location("hermes_alive_lifecycle_matrix", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def swap_rollback_injection() -> None:
    module = load_lifecycle_module()
    base = Path(tempfile.mkdtemp(prefix="swap-rollback-"))
    target = base / "target"
    stage = base / "stage"
    rollback = base / "rollback"
    target.mkdir()
    stage.mkdir()
    (target / "value").write_text("old", encoding="utf-8")
    (stage / "value").write_text("new", encoding="utf-8")
    real = module.os.replace
    calls = {"count": 0}
    def injected(src, dst):
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("injected_replace_failure")
        return real(src, dst)
    module.os.replace = injected
    try:
        try:
            module._swap_directory(stage, target, rollback)
        except OSError:
            pass
        else:
            raise AssertionError("injected failure not raised")
    finally:
        module.os.replace = real
    assert (target / "value").read_text(encoding="utf-8") == "old"


def manifest_failure_transaction_rollback() -> None:
    module = load_lifecycle_module()
    home = Path(tempfile.mkdtemp(prefix="manifest-rollback-"))
    old = Path(tempfile.mkdtemp(prefix="manifest-old-")) / "skill"
    new = Path(tempfile.mkdtemp(prefix="manifest-new-")) / "skill"
    shutil.copytree(SKILL, old)
    shutil.copytree(SKILL, new)
    (old / "TEST_VERSION").write_text("old", encoding="utf-8")
    (new / "TEST_VERSION").write_text("new", encoding="utf-8")
    first = lifecycle_cmd(home, "install", "--source-root", str(old), source=old)
    assert first.returncode == 0, first.stdout
    args = SimpleNamespace(
        hermes_home=str(home), source_root=str(new), source_target=None,
        hook_target=None, shared_dir=str(home / "hermes_alive_shared"),
    )
    real = module._write_manifest
    module._write_manifest = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("injected_manifest_failure"))
    try:
        try:
            module.install(args)
        except RuntimeError as exc:
            assert "injected_manifest_failure" in str(exc)
        else:
            raise AssertionError("manifest failure not raised")
    finally:
        module._write_manifest = real
    target = home / "skills" / "hermes" / "hermes-alive"
    assert (target / "TEST_VERSION").read_text(encoding="utf-8") == "old"
    assert lifecycle_cmd(home, "verify").returncode == 0


def permissions_under_umask_zero() -> None:
    home = Path(tempfile.mkdtemp(prefix="umask-zero-"))
    command = [sys.executable, str(SCRIPTS / "hermes-alive-lifecycle.py"), "install", "--hermes-home", str(home), "--source-root", str(SKILL)]
    env = dict(os.environ)
    env["HERMES_ALIVE_SHARED_DIR"] = str(home / "hermes_alive_shared")
    result = subprocess.run(["/bin/sh", "-lc", "umask 000; exec \"$@\"", "sh", *command], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert result.returncode == 0, result.stdout
    assert oct((home / "hermes_alive_shared" / "install").stat().st_mode & 0o777) == "0o700"
    assert oct((home / "hermes_alive_shared" / "install" / "manifest.json").stat().st_mode & 0o777) == "0o600"
    offenders = [path for path in home.rglob("*") if path.stat().st_mode & 0o002]
    assert not offenders, offenders[:10]


def no_secret_output() -> None:
    home = Path(tempfile.mkdtemp(prefix="secret-output-"))
    secret = "sk-" + "test-super-secret-value"
    env = dict(os.environ)
    env["OPENAI_API_KEY"] = secret
    env["HERMES_ALIVE_SHARED_DIR"] = str(home / "hermes_alive_shared")
    result = subprocess.run([sys.executable, str(SCRIPTS / "hermes-alive-lifecycle.py"), "configure", "--provider-check-only", "--hermes-home", str(home)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
    assert secret not in result.stdout


def main() -> int:
    runner = Runner()
    cases = [
        ("provider_missing", provider_missing),
        ("provider_configured", provider_configured),
        ("provider_malformed", provider_malformed),
        ("managed_absent", managed_absent),
        ("managed_valid_and_override", managed_valid_and_override),
        ("managed_corrupt", managed_corrupt),
        ("policy_matrix", policy_matrix),
        ("delivery_plans", delivery_plans),
        ("delivery_send_matrix", delivery_send_matrix),
        ("content_ref_hidden", content_ref_hidden),
        ("learning_matrix", learning_matrix),
        ("watcher_metadata_and_reference", watcher_metadata_and_reference),
        ("lifecycle_matrix", lifecycle_matrix),
        ("lifecycle_compile_failure_preserves_previous", lifecycle_compile_failure_preserves_previous),
        ("swap_rollback_injection", swap_rollback_injection),
        ("manifest_failure_transaction_rollback", manifest_failure_transaction_rollback),
        ("permissions_under_umask_zero", permissions_under_umask_zero),
        ("no_secret_output", no_secret_output),
    ]
    for name, func in cases:
        runner.run(name, func)
    return runner.finish()


if __name__ == "__main__":
    raise SystemExit(main())
