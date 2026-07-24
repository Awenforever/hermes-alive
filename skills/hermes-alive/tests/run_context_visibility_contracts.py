#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import importlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import types

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
sys.path.insert(0, str(HOOKS))

tmp = Path(tempfile.mkdtemp(prefix="ha-context-visibility-test-"))
shared = tmp / "shared"
shared.mkdir()
locks = shared / "locks"
locks.mkdir()
db_path = tmp / "state.db"

os.environ["HERMES_ALIVE_SHARED_DIR"] = str(shared)
os.environ["HERMES_STATE_DB"] = str(db_path)
os.environ["HERMES_HOME"] = str(tmp)
os.environ["HERMES_PROACTIVE_WEIXIN_CHAT_ID"] = "user-1"

safe_io = types.ModuleType("safe_io")
safe_io.LOCK_DIR = locks

@contextlib.contextmanager
def file_lock(_path):
    yield

def locked_read_json(path, default, _lock_name):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default

def atomic_write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

safe_io.file_lock = file_lock
safe_io.locked_read_json = locked_read_json
safe_io.atomic_write_json = atomic_write_json
safe_io.append_jsonl = lambda *args, **kwargs: None
safe_io.try_file_lock = file_lock
safe_io.sha256_text = lambda value: __import__("hashlib").sha256(
    str(value).encode("utf-8")
).hexdigest()
safe_io.redact_preview = lambda value: str(value)[:40]
safe_io.atomic_write_text = lambda path, value: Path(path).write_text(
    str(value), encoding="utf-8"
)
sys.modules["safe_io"] = safe_io

weixin_peer = types.ModuleType("weixin_peer")
weixin_peer.resolve_weixin_peer = lambda _value="": ("user-1", "test")
weixin_peer.adapter_context_token_present = lambda: False
sys.modules["weixin_peer"] = weixin_peer

voice_engine = types.ModuleType("voice_engine")
voice_engine.extract_user_style_signals = lambda _messages: {}
voice_engine.STYLE_DIMENSIONS = ()
sys.modules["voice_engine"] = voice_engine

conn = sqlite3.connect(db_path)
conn.executescript(
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
conn.execute(
    "INSERT INTO sessions(id, source, user_id) VALUES (?, ?, ?)",
    ("s1", "weixin", "user-1"),
)
now = time.time()
rows = [
    (1, "s1", "assistant", "", now - 500, 1),
    (2, "s1", "user", "/continue", now - 400, 1),
    (3, "s1", "user", "正在核对 release-v3.tar.gz", now - 300, 1),
    (4, "s1", "assistant", "第一段回复", now - 250, 1),
    (5, "s1", "assistant", "第二段回复", now - 200, 1),
]
conn.executemany(
    "INSERT INTO messages(id, session_id, role, content, timestamp, active) "
    "VALUES (?, ?, ?, ?, ?, ?)",
    rows,
)
conn.commit()
conn.close()

context_tracker = importlib.import_module("context_tracker")

queue = context_tracker.refresh_context_queue()
messages = queue["messages"]
assert len(messages) == 2, messages
assert [item["role"] for item in messages] == ["user", "assistant"], messages
assert "/continue" not in json.dumps(messages, ensure_ascii=False)
assert "第一段回复" in messages[-1]["content_snippet"]
assert "第二段回复" in messages[-1]["content_snippet"]

bundle = context_tracker.build_prompt_context(refresh=True, now=now)
meta = bundle["metadata"]
assert meta["queue_healthy"] is True, meta
assert meta["context_prompt_eligible_count"] == 2, meta
assert meta["queue_user_message_count"] == 1, meta
assert meta["referent_anchor_count"] >= 1, meta
assert "release-v3.tar.gz" in bundle["text"]

stale = {
    "version": 1,
    "updated_at": "old",
    "messages": [
        {
            "role": "assistant",
            "timestamp": now - 10000,
            "content_snippet": "stale",
            "session_id": "old",
            "message_id": 999,
        }
    ],
}
context_tracker.QUEUE_FILE.write_text(
    json.dumps(stale),
    encoding="utf-8",
)
rebuilt = context_tracker.refresh_context_queue()
assert all(
    item.get("content_snippet") != "stale"
    for item in rebuilt["messages"]
)

session_context = {"session_id": "active-session"}
context_tracker.set_session_busy(session_context)
context_tracker._session_busy = False
assert context_tracker.is_session_busy() is True
lease = context_tracker.activity_lease_snapshot()
assert lease["lease_count"] == 1, lease
context_tracker.set_session_idle(session_context)
assert context_tracker.is_session_busy() is False

semantic = importlib.import_module("semantic_bubbles")
good_snapshot = {
    "queue_healthy": True,
    "context_prompt_eligible_count": 2,
}
empty_snapshot = {
    "queue_healthy": True,
    "context_prompt_eligible_count": 0,
}

def expect_error(payload, expected, snapshot):
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

expect_error(
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

expect_error(
    {
        "topic_mode": "context_continuation",
        "bubbles": [
            {
                "act": "debug_companion",
                "text": "release-v3.tar.gz 这个包还在验证吗？",
            }
        ],
    },
    "context_continuation_without_visible_healthy_context",
    empty_snapshot,
)

plan = semantic.parse_semantic_plan(
    json.dumps(
        {
            "topic_mode": "context_continuation",
            "bubbles": [
                {
                    "act": "debug_companion",
                    "text": "release-v3.tar.gz 这个包还在验证吗？",
                }
            ],
        },
        ensure_ascii=False,
    ),
    default_msg_type="debug_companion",
    context_snapshot=good_snapshot,
)
assert len(plan.bubbles) == 1

composer_source = (HOOKS / "llm_message_composer.py").read_text(
    encoding="utf-8"
)
for forbidden in (
    "这包别再炸了",
    "你可以说：\"你继续，我不插嘴\"",
):
    assert forbidden not in composer_source, forbidden
assert "无可见近期上下文" in composer_source
assert "last_context_snapshot" in composer_source

watcher_source = (HOOKS / "proactive_watcher.py").read_text(
    encoding="utf-8"
)
for marker in (
    'stage="pre_discovery"',
    'stage="post_discovery_pre_compose"',
    'stage="post_compose_pre_send"',
    "context_prompt_eligible_count",
    "context_prompt_hash",
    "referent_anchor_count",
):
    assert marker in watcher_source, marker
assert "allow_when_user_active" not in watcher_source
assert "context_queue_unhealthy" in watcher_source

handler_source = (HOOKS / "handler.py").read_text(encoding="utf-8")
assert "set_session_busy(context" in handler_source
assert "set_session_idle(context" in handler_source

print("CONTEXT_VISIBILITY_CONTRACT_TESTS=PASS")
print("effective_queue_filtering=PASS")
print("recent_context_under_30_minutes_visible=PASS")
print("cross_process_activity_lease=PASS")
print("continue_context_exclusion=PASS")
print("deictic_referent_grounding=PASS")
print("context_continuation_visibility_gate=PASS")
print("three_stage_activity_guard=PASS")
print("safe_context_observability=PASS")
