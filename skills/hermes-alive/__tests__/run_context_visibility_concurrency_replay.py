#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import importlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import time

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
TEST_ROOT = Path(tempfile.mkdtemp(prefix="ha-context-concurrency-replay-"))
SUPPORT = TEST_ROOT / "support"
SUPPORT.mkdir(parents=True)
SHARED = TEST_ROOT / "shared"
SHARED.mkdir(parents=True)
(SHARED / "locks").mkdir(parents=True)
DB = TEST_ROOT / "state.db"


def write_support_modules() -> None:
    (SUPPORT / "safe_io.py").write_text(
        textwrap.dedent(
            '''
            from __future__ import annotations
            import contextlib
            import fcntl
            import hashlib
            import json
            import os
            from pathlib import Path
            import tempfile

            LOCK_DIR = Path(os.environ["HERMES_ALIVE_SHARED_DIR"]) / "locks"
            LOCK_DIR.mkdir(parents=True, exist_ok=True)

            @contextlib.contextmanager
            def file_lock(path):
                path = Path(path)
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("a+") as handle:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                    try:
                        yield
                    finally:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

            @contextlib.contextmanager
            def try_file_lock(path):
                with file_lock(path):
                    yield True

            def _atomic_write(path, text):
                path = Path(path)
                path.parent.mkdir(parents=True, exist_ok=True)
                fd, temp_name = tempfile.mkstemp(
                    prefix=path.name + ".",
                    dir=path.parent,
                )
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as handle:
                        handle.write(text)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temp_name, path)
                finally:
                    try:
                        os.unlink(temp_name)
                    except FileNotFoundError:
                        pass

            def atomic_write_json(path, data):
                _atomic_write(
                    path,
                    json.dumps(data, ensure_ascii=False, indent=2) + "\\n",
                )

            def locked_read_json(path, default, lock_name):
                with file_lock(LOCK_DIR / lock_name):
                    try:
                        return json.loads(Path(path).read_text(encoding="utf-8"))
                    except Exception:
                        return default

            def locked_write_json(path, data, lock_name):
                with file_lock(LOCK_DIR / lock_name):
                    atomic_write_json(path, data)

            def atomic_write_text(path, value):
                _atomic_write(path, str(value))

            def append_jsonl(path, item, lock_name=None):
                lock_path = LOCK_DIR / (
                    lock_name or (Path(path).name + ".lock")
                )
                with file_lock(lock_path):
                    path = Path(path)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with path.open("a", encoding="utf-8") as handle:
                        handle.write(
                            json.dumps(item, ensure_ascii=False) + "\\n"
                        )

            def sha256_text(value):
                return hashlib.sha256(str(value).encode("utf-8")).hexdigest()

            def redact_preview(value):
                return str(value)[:40]
            '''
        ).lstrip(),
        encoding="utf-8",
    )
    (SUPPORT / "weixin_peer.py").write_text(
        "def resolve_weixin_peer(value=''): return ('user-1', 'test')\n"
        "def adapter_context_token_present(): return False\n",
        encoding="utf-8",
    )
    (SUPPORT / "voice_engine.py").write_text(
        textwrap.dedent(
            '''
            STYLE_DIMENSIONS = ()
            def extract_user_style_signals(messages):
                return {}
            class _Genome:
                relationship_stage = "acquaintance"
            class VoiceEngine:
                def __init__(self):
                    self.genome = _Genome()
                    self.message_count = 0
                    self.social_urge = 0.5
                def on_interaction_start(self, context):
                    return None
                def on_agent_end(self, signals):
                    return None
                def snapshot_prompt(self):
                    return ""
            '''
        ).lstrip(),
        encoding="utf-8",
    )
    (SUPPORT / "circadian_intent_bridge.py").write_text(
        "def process_latest_user_intent_shadow():\n"
        "    return {\"processed\": False, \"reason\": \"isolated_test\", "
        "\"state_event_applied\": False}\n",
        encoding="utf-8",
    )


def make_env(shared: Path, db: Path, ttl: str = "120") -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PYTHONPATH": f"{SUPPORT}:{HOOKS}",
            "HERMES_ALIVE_SHARED_DIR": str(shared),
            "HERMES_STATE_DB": str(db),
            "HERMES_HOME": str(TEST_ROOT),
            "HERMES_PROACTIVE_WEIXIN_CHAT_ID": "user-1",
            "HERMES_ALIVE_ACTIVITY_LEASE_TTL_SECONDS": ttl,
            "HERMES_PROACTIVE_PLATFORM_ENABLED": "false",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return env


def make_db(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE sessions (
          id TEXT PRIMARY KEY,
          source TEXT,
          user_id TEXT
        );
        CREATE TABLE messages (
          id INTEGER PRIMARY KEY,
          session_id TEXT,
          role TEXT,
          content TEXT,
          timestamp REAL,
          active INTEGER
        );
        """
    )
    connection.execute(
        "INSERT INTO sessions(id, source, user_id) VALUES (?, ?, ?)",
        ("s-main", "weixin", "user-1"),
    )
    for index in range(1, 5):
        connection.execute(
            "INSERT INTO sessions(id, source, user_id) VALUES (?, ?, ?)",
            (f"s-{index}", "weixin", "user-1"),
        )
    connection.execute(
        "INSERT INTO sessions(id, source, user_id) VALUES (?, ?, ?)",
        ("subagent-task", "subagent", "user-1"),
    )
    connection.commit()
    connection.close()


def run_child(code: str, *args: str, env: dict[str, str]) -> str:
    result = subprocess.run(
        [sys.executable, "-c", code, *args],
        env=env,
        check=True,
        text=True,
        capture_output=True,
        timeout=60,
    )
    return result.stdout


write_support_modules()
make_db(DB)
ENV = make_env(SHARED, DB)
os.environ.update(
    {
        key: value
        for key, value in ENV.items()
        if key.startswith("HERMES_")
    }
)
sys.path[:0] = [str(SUPPORT), str(HOOKS)]

# ---------------------------------------------------------------------------
# 1. Shared lease concurrency: concurrent writers must not lose leases.
# ---------------------------------------------------------------------------
lease_writer = (
    "import sys\n"
    "from context_tracker import set_session_busy\n"
    "set_session_busy({'session_id': sys.argv[1], 'source': 'subagent'})\n"
)
processes = [
    subprocess.Popen(
        [sys.executable, "-c", lease_writer, f"lease-{index}"],
        env=ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    for index in range(8)
]
for process in processes:
    stdout, stderr = process.communicate(timeout=60)
    assert process.returncode == 0, (stdout, stderr)

context_tracker = importlib.import_module("context_tracker")
lease_snapshot = context_tracker.activity_lease_snapshot()
assert lease_snapshot["busy"] is True, lease_snapshot
assert lease_snapshot["lease_count"] == 8, lease_snapshot
lease_file_text = context_tracker.ACTIVITY_FILE.read_text(encoding="utf-8")
assert "lease-" not in lease_file_text

for index in range(8):
    context_tracker.set_session_idle(
        {"session_id": f"lease-{index}", "source": "subagent"}
    )
assert context_tracker.is_session_busy() is False
print("CONCURRENCY_PASS shared_activity_lease_8_writers")

# ---------------------------------------------------------------------------
# 2. Crash recovery: an orphaned lease must expire under the configured TTL.
# ---------------------------------------------------------------------------
crash_shared = TEST_ROOT / "crash-shared"
crash_shared.mkdir()
(crash_shared / "locks").mkdir()
crash_db = TEST_ROOT / "crash-state.db"
make_db(crash_db)
crash_env = make_env(crash_shared, crash_db, ttl="0.35")
run_child(lease_writer, "crashed-session", env=crash_env)
time.sleep(0.55)
crash_snapshot_text = run_child(
    "import json\n"
    "from context_tracker import activity_lease_snapshot\n"
    "print(json.dumps(activity_lease_snapshot(), sort_keys=True))\n",
    env=crash_env,
)
crash_snapshot = json.loads(crash_snapshot_text.strip())
assert crash_snapshot["busy"] is False, crash_snapshot
assert crash_snapshot["lease_count"] == 0, crash_snapshot
print("CONCURRENCY_PASS orphaned_activity_lease_ttl_recovery")

# ---------------------------------------------------------------------------
# 3. Queue refresh race with empty/control/tool-like noise and many sessions.
# ---------------------------------------------------------------------------
now = time.time()
connection = sqlite3.connect(DB)
message_id = 1
rows = []
for index in range(1, 241):
    session = f"s-{(index % 4) + 1}"
    role = "user" if index % 3 == 0 else "assistant"
    if index % 19 == 0:
        content = ""
    elif role == "user" and index % 23 == 0:
        content = "/continue"
    elif role == "user":
        content = f"正在处理 hermes-context-{index}.tar.gz"
    else:
        content = f"回复片段 {index}"
    rows.append(
        (message_id, session, role, content, now - 2000 + index, 1)
    )
    message_id += 1

# Explicit same-role fragments near the tail must collapse.
rows.extend(
    [
        (message_id, "s-main", "user", "请核对 context-fix-v1.tar.gz", now - 25, 1),
        (message_id + 1, "s-main", "assistant", "第一段", now - 20, 1),
        (message_id + 2, "s-main", "assistant", "第二段", now - 10, 1),
        (message_id + 3, "subagent-task", "user", "外部任务活动", now - 5, 1),
    ]
)
connection.executemany(
    "INSERT INTO messages(id, session_id, role, content, timestamp, active) "
    "VALUES (?, ?, ?, ?, ?, ?)",
    rows,
)
connection.commit()
connection.close()

refresh_code = (
    "from context_tracker import refresh_context_queue\n"
    "for _ in range(5): refresh_context_queue()\n"
)
reader_code = (
    "import json, os, time\n"
    "from pathlib import Path\n"
    "path=Path(os.environ['HERMES_ALIVE_SHARED_DIR'])/'context_queue.json'\n"
    "for _ in range(200):\n"
    "  if path.exists(): json.loads(path.read_text())\n"
    "  time.sleep(0.001)\n"
)
workers = [
    subprocess.Popen(
        [sys.executable, "-c", refresh_code],
        env=ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    for _ in range(6)
]
readers = [
    subprocess.Popen(
        [sys.executable, "-c", reader_code],
        env=ENV,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    for _ in range(2)
]
for process in workers + readers:
    stdout, stderr = process.communicate(timeout=120)
    assert process.returncode == 0, (stdout, stderr)

queue = context_tracker.refresh_context_queue()
expected = context_tracker._QUEUE.expected_from_state_db()
assert queue["messages"] == expected
assert len(queue["messages"]) <= 30
assert any(item["role"] == "user" for item in queue["messages"])
assert len({item["session_id"] for item in queue["messages"]}) >= 2
assert all(item["content_snippet"].strip() for item in queue["messages"])
assert all(
    not item["content_snippet"].lstrip().startswith("/")
    for item in queue["messages"]
)
joined = "\n".join(item["content_snippet"] for item in queue["messages"])
assert "第一段" in joined and "第二段" in joined
assert "外部任务活动" not in joined

prompt = context_tracker.build_prompt_context(refresh=True, now=now)
metadata = prompt["metadata"]
assert metadata["queue_healthy"] is True, metadata
assert metadata["context_prompt_eligible_count"] > 0, metadata
assert metadata["referent_anchor_count"] > 0, metadata
assert "context-fix-v1.tar.gz" in prompt["text"]
assert "content_snippet" not in json.dumps(metadata, ensure_ascii=False)
print("CONCURRENCY_PASS queue_refresh_atomicity_and_effective_turns")

# ---------------------------------------------------------------------------
# 4. Subagent activity lifecycle must bridge into the shared lease.
# ---------------------------------------------------------------------------
handler = importlib.import_module("handler")
subagent_context = {
    "session_id": "subagent-live-task",
    "source": "subagent",
}
asyncio.run(handler._on_session_start(subagent_context))
context_tracker._session_busy = False
assert context_tracker.is_session_busy() is True
asyncio.run(handler._on_agent_end(subagent_context))
assert context_tracker.is_session_busy() is False
print("INCIDENT_REPLAY_PASS subagent_activity_lease_bridge")

# ---------------------------------------------------------------------------
# 5. Exact incident phrase and vague referents must be rejected.
# ---------------------------------------------------------------------------
semantic = importlib.import_module("semantic_bubbles")


def expect_semantic_error(payload, expected, snapshot):
    try:
        semantic.parse_semantic_plan(
            json.dumps(payload, ensure_ascii=False),
            default_msg_type="debug_companion",
            context_snapshot=snapshot,
        )
    except semantic.SemanticPlanError as exc:
        assert str(exc) == expected, (str(exc), expected)
    else:
        raise AssertionError(expected)


empty_snapshot = {
    "queue_healthy": True,
    "context_prompt_eligible_count": 0,
}
healthy_snapshot = {
    "queue_healthy": True,
    "context_prompt_eligible_count": 3,
}
expect_semantic_error(
    {
        "topic_mode": "ambient",
        "bubbles": [
            {
                "act": "debug_companion",
                "text": "还在跟那个包较劲？",
            }
        ],
    },
    "ungrounded_deictic_reference",
    empty_snapshot,
)
expect_semantic_error(
    {
        "topic_mode": "context_continuation",
        "bubbles": [
            {
                "act": "debug_companion",
                "text": "context-fix-v1.tar.gz 还在验证吗？",
            }
        ],
    },
    "context_continuation_without_visible_healthy_context",
    empty_snapshot,
)
accepted = semantic.parse_semantic_plan(
    json.dumps(
        {
            "topic_mode": "context_continuation",
            "bubbles": [
                {
                    "act": "debug_companion",
                    "text": "context-fix-v1.tar.gz 还在验证吗？",
                }
            ],
        },
        ensure_ascii=False,
    ),
    default_msg_type="debug_companion",
    context_snapshot=healthy_snapshot,
)
assert len(accepted.bubbles) == 1
print("INCIDENT_REPLAY_PASS exact_vague_package_phrase_rejected")

# ---------------------------------------------------------------------------
# 6. Exercise the real tick flow with activity beginning at every boundary.
# ---------------------------------------------------------------------------
watcher_module = importlib.import_module("proactive_watcher")


class SendResult:
    success = True


class FakeAdapter:
    def __init__(self):
        self.sent: list[str] = []

    async def send(self, chat_id, content, metadata=None):
        self.sent.append(content)
        return SendResult()


class TestWatcher(watcher_module.ProactivePlatformWatcher):
    def __init__(self, activity_sequence, messages=None, delivery=None):
        self.adapter = FakeAdapter()
        super().__init__({"weixin": self.adapter}, None)
        self.activity_sequence = iter(activity_sequence)
        self.logs: list[dict[str, object]] = []
        self.test_messages = messages or [
            ("debug_companion", "完整的新话题。", "model")
        ]
        self.test_delivery = delivery

    @property
    def enabled(self):
        return True

    def _resolve_adapter_and_chat_id(self):
        return self.adapter, "chat"

    async def _process_control_queue(self, *args):
        return False

    def _circadian_shadow_decision(self, **kwargs):
        return None

    def _sleep_quiet_policy_shadow_decision(self, *args, **kwargs):
        return None

    def _voice_state(self):
        return None

    def _user_active_recently(self):
        value = bool(next(self.activity_sequence))
        self._last_activity_snapshot = {
            "queue_healthy": not value,
            "session_busy": value,
            "activity_guard_reason_code": "test_active" if value else "test_idle",
        }
        return value

    def _proactive_quality_shadow_decision(self, **kwargs):
        return None

    def _quality_precompose_enforcement(self, *args):
        return None

    def _evaluate_interruption_policy(self, **kwargs):
        return {
            "allow_send": True,
            "allow_content_share": True,
            "mode": "ambient",
            "max_bubbles": 5,
        }

    def _cooldown(self):
        return None

    async def _check_discovery(self):
        return {"external": [{"id": "item-1", "title": "T"}], "local": []}

    def _log_discovery(self, *args, **kwargs):
        return None

    async def _check_dream(self):
        return None

    async def _compose_message(self, *args, **kwargs):
        return list(self.test_messages)

    def _content_reference_generated_by(self, *args):
        return None

    def _extract_content_reference(self, messages):
        return messages, None

    def _enforce_policy_messages(self, messages, policy):
        return messages

    def _content_delivery(self):
        return self.test_delivery

    def _quality_candidate_shadow_audits(self, *args):
        return []

    def _apply_quality_enforcement(self, messages, *args):
        return messages, None

    def _metadata(self, *args):
        return {}

    def _commit_quality_delivery(self, *args):
        return None

    def _record_interest_delivery(self, *args, **kwargs):
        return None

    def _log_compose(self, *args, **kwargs):
        return None

    def _log(self, event, **kwargs):
        self.logs.append({"event": event, **kwargs})


async def run_stage_cases():
    cases = [
        ([True], 0),
        ([False, True], 0),
        ([False, False, True], 0),
        ([False, False, False, True], 0),
        ([False, False, False, False], 1),
    ]
    for sequence, expected_sends in cases:
        watcher = TestWatcher(sequence)
        await watcher._tick_impl("stage-test")
        assert len(watcher.adapter.sent) == expected_sends, (
            sequence,
            watcher.adapter.sent,
            watcher.logs,
        )


asyncio.run(run_stage_cases())
print("CONCURRENCY_PASS activity_guard_all_boundaries")

# Multi-bubble burst: activity after bubble 1 must suppress bubble 2.
original_sleep = watcher_module.asyncio.sleep


async def no_sleep(_seconds):
    return None


watcher_module.asyncio.sleep = no_sleep
try:
    multi = TestWatcher(
        [False, False, False, False, True],
        messages=[
            ("discovery_intro", "第一条完整信息。", "model"),
            ("source_link", "第二条链接信息。", "model"),
        ],
    )
    asyncio.run(multi._tick_impl("multi-bubble-race"))
    assert multi.adapter.sent == ["第一条完整信息。"], multi.adapter.sent
finally:
    watcher_module.asyncio.sleep = original_sleep
print("CONCURRENCY_PASS activity_interrupts_remaining_bubbles")

# Rich-only delivery: the final rich send must have its own activity guard.
class RichPayload:
    generated_by = "model"
    kind = "link_card"
    content_item_id = "item-1"


class Plan:
    text_messages = []
    rich_payload = RichPayload()
    selected_item = {"id": "item-1"}
    evidence_score = 1.0
    max_units = 1


class RichOutcome:
    success = True
    kind = "link_card"
    mode = "rich"
    content_delivered = True
    fallback_used = False
    error = None


class FakeDelivery:
    def __init__(self):
        self.rich_calls = 0

    def plan(self, *args, **kwargs):
        return Plan()

    async def send_text(self, *args, **kwargs):
        raise AssertionError("no text expected")

    async def send_rich(self, *args, **kwargs):
        self.rich_calls += 1
        return RichOutcome()


rich_delivery = FakeDelivery()
rich_watcher = TestWatcher(
    [False, False, False, True],
    messages=[("debug_companion", "placeholder", "model")],
    delivery=rich_delivery,
)
asyncio.run(rich_watcher._tick_impl("rich-race"))
assert rich_delivery.rich_calls == 0
print("CONCURRENCY_PASS activity_blocks_rich_send")

# ---------------------------------------------------------------------------
# 7. Source and privacy assertions.
# ---------------------------------------------------------------------------
watcher_source = (HOOKS / "proactive_watcher.py").read_text(encoding="utf-8")
composer_source = (HOOKS / "llm_message_composer.py").read_text(encoding="utf-8")
for marker in (
    'stage="pre_discovery"',
    'stage="post_discovery_pre_compose"',
    'stage="post_compose_pre_send"',
    'stage="pre_text_send"',
    'stage="pre_rich_send"',
    "user_active_before_text_send",
    "user_active_before_rich_send",
):
    assert marker in watcher_source, marker
for forbidden in (
    "这包别再炸了",
    "审包、跑脚本、处理 NAS/Hermes",
):
    assert forbidden not in composer_source, forbidden

safe_log_blob = json.dumps(
    [entry for entry in multi.logs if entry.get("event") == "activity_guard"],
    ensure_ascii=False,
)
assert "第一条完整信息" not in safe_log_blob
assert "第二条链接信息" not in safe_log_blob
assert "context_prompt_hash" not in safe_log_blob or "content_snippet" not in safe_log_blob
print("PRIVACY_PASS no_raw_context_in_activity_guard_logs")

# Deterministic performance loop for referent rejection and activity snapshots.
start = time.perf_counter()
for _ in range(10000):
    try:
        semantic.parse_semantic_plan(
            json.dumps(
                {
                    "topic_mode": "ambient",
                    "bubbles": [
                        {"act": "debug_companion", "text": "还在弄那个？"}
                    ],
                },
                ensure_ascii=False,
            ),
            default_msg_type="debug_companion",
            context_snapshot=empty_snapshot,
        )
    except semantic.SemanticPlanError:
        pass
elapsed = time.perf_counter() - start
assert elapsed < 20.0, elapsed
print(
    "PERFORMANCE_PASS semantic_referent_rejections_10000 "
    + json.dumps({"elapsed_seconds": round(elapsed, 4)})
)

print(
    json.dumps(
        {
            "result": "PASS",
            "lease_concurrent_writers": 8,
            "queue_refresh_workers": 6,
            "queue_reader_workers": 2,
            "queue_reader_iterations_each": 200,
            "semantic_replay_iterations": 10000,
            "incident_phrase": "hash-only-in-production; literal-used-only-in-isolated-test",
        },
        ensure_ascii=False,
        indent=2,
    )
)
print("HERMES_ALIVE_CONTEXT_CONCURRENCY_INCIDENT_REPLAY_RESULT=PASS")
sys.stdout.flush()
sys.stderr.flush()
os._exit(0)
