"""DreamEngine — 4-phase memory consolidation for Hermes Alive.

Wired into the proactive_watcher tick loop. Reads current memory state
in Phase 1, sends a dream prompt to the auxiliary LLM in Phase 2–4,
and produces a non-destructive DreamDiff for review. After diff generation,
applies high-confidence operations to memory and fact_store, and evolves voice.

Usage:
    engine = DreamEngine()
    if engine.should_run():
        diff = await engine.run_dream_cycle()
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

# Absolute imports (hook files are loaded flat by importlib)
from dream_diff_store import DreamDiff, load_latest_diff, save_diff
from dream_prompt import (
    DEFAULT_DREAM_INTERVAL_HOURS,
    DREAM_ENABLED_ENV,
    DREAM_INTERVAL_ENV,
    DREAM_SYSTEM_PROMPT,
    MEMORY_CHAR_LIMIT,
)

logger = logging.getLogger(__name__)

# The Weixin user to track (matched by source + user_id in sessions table)
WEIXIN_SOURCE = "weixin"
HERMES_HOME = os.getenv("HERMES_HOME", "/opt/data")
STATE_DB_PATH = os.getenv("HERMES_STATE_DB", os.path.join(HERMES_HOME, "state.db"))


def _weixin_user_id() -> str:
    try:
        from weixin_peer import resolve_weixin_peer

        resolved, _reason = resolve_weixin_peer(
            os.getenv(
                "HERMES_PROACTIVE_WEIXIN_CHAT_ID",
                "",
            )
        )
        return resolved
    except Exception:
        return os.getenv(
            "HERMES_PROACTIVE_WEIXIN_CHAT_ID",
            "",
        ).strip()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dream_enabled() -> bool:
    val = os.getenv(DREAM_ENABLED_ENV, "false").strip().lower()
    return val in {"1", "true", "yes", "on"}


def _dream_interval_seconds() -> int:
    hours = int(os.getenv(DREAM_INTERVAL_ENV, str(DEFAULT_DREAM_INTERVAL_HOURS)))
    return max(3600, hours * 3600)


class DreamEngine:
    """Orchestrates the 4-phase dream consolidation cycle."""

    def __init__(self, diff_path: str | None = None) -> None:
        self._diff_path = diff_path or os.getenv(
                    "DREAM_DIFF_PATH", os.path.join(os.getenv("HERMES_HOME", "/opt/data"), "hermes_alive_shared", "dream_diff.json")
                )

    def should_run(self) -> bool:
        if not _dream_enabled():
            return False
        last = self._read_last_dream_timestamp()
        if last is not None:
            elapsed = time.time() - last
            if elapsed < _dream_interval_seconds():
                return False
        return True

    async def run_dream_cycle(self) -> DreamDiff:
        diff = DreamDiff()
        diff.timestamp = _now_iso()

        try:
            # Phase 1: Orient — read current memory state + real session transcripts
            orient = self._orient()
            diff.orient_summary = orient

            # Phase 2–4: Gather + Consolidate + Prune via LLM
            operations = await self._gather(orient)
            ops, prunes = self._consolidate(operations, orient)
            diff.operations = ops or []
            diff.prune_candidates = prunes or []
            diff.summary = self._prune(diff)

            # ── P2: Apply high-confidence operations to memory and fact_store ──
            applied_ops = self._apply_operations(diff)
            if applied_ops > 0:
                diff.applied = True
                diff.applied_at = datetime.now(timezone.utc).isoformat()
                diff.summary += f" Applied {applied_ops} high-confidence operation(s)."

            logger.info(
                "Dream cycle: %d ops, %d prunes — %s",
                len(diff.operations), len(diff.prune_candidates), diff.summary,
            )

            # ── P3: Dream voice adjustment ──
            self._adjust_voice(diff)

        except Exception:
            logger.exception("Dream cycle failed")
            diff.summary = "Dream cycle failed with an error."

        save_diff(diff, self._diff_path)
        return diff

    # ── Phase 1: Orient ──────────────────────────────────────────────────

    def _orient(self) -> dict:
        """Scan current memory state from filesystem and state.db sessions."""
        orient: dict = {
            "memory_files": 0,
            "fact_count": 0,
            "sessions_reviewed": 0,
            "memory_chars_used": 0,
            "memory_chars_limit": MEMORY_CHAR_LIMIT,
            "timestamp": _now_iso(),
            "memory_content": "",
            "user_content": "",
            "session_transcripts": [],
        }

        # Read MEMORY.md
        memory_paths = [
            os.getenv("HERMES_HOME", "/opt/data") + "/memories/MEMORY.md",
        ]
        for mp in memory_paths:
            try:
                if os.path.isfile(mp):
                    with open(mp, "r", encoding="utf-8") as f:
                        content = f.read()
                    orient["memory_content"] = content
                    orient["memory_chars_used"] = len(content)
                    orient["memory_files"] = 1
                    break
            except (OSError, UnicodeDecodeError):
                pass

        # Read proactive_context.md (user profile)
        context_paths = [
            os.getenv("HERMES_HOME", "/opt/data") + "/proactive_context.md",
            "/opt/data/proactive_context.md",
        ]
        for cp in context_paths:
            try:
                if os.path.isfile(cp):
                    with open(cp, "r", encoding="utf-8") as f:
                        orient["user_content"] = f.read()
                    break
            except (OSError, UnicodeDecodeError):
                pass

        # ── P1: Read real session transcripts from state.db ──
        try:
            transcripts = self._read_session_transcripts()
            orient["session_transcripts"] = transcripts
            orient["sessions_reviewed"] = len(transcripts)
        except Exception:
            logger.exception("Failed to read session transcripts from state.db")
            orient["session_transcripts"] = []
            orient["sessions_reviewed"] = -1

        return orient

    def _read_session_transcripts(self) -> list[dict]:
        """Read recent 3-5 session transcripts from state.db.

        For each session, capture first 500 chars and last 300 chars
        of the conversation (beginning and end are most informative).
        """
        db_path = os.getenv("HERMES_STATE_DB", STATE_DB_PATH)
        if not os.path.isfile(db_path):
            logger.debug("state.db not found at %s", db_path)
            return []

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()

            user_id = _weixin_user_id()
            if not user_id:
                logger.debug("No WEIXIN_CHAT_ID configured; cannot read session transcripts")
                return []

            # Find recent Weixin DM session IDs (last 5)
            cursor.execute(
                "SELECT id, started_at FROM sessions "
                "WHERE source = ? AND user_id = ? ORDER BY started_at DESC LIMIT 5",
                (WEIXIN_SOURCE, user_id)
            )
            sessions = cursor.fetchall()
            if not sessions:
                logger.debug("No Weixin sessions found in state.db")
                return []

            transcripts = []
            for sess in sessions:
                session_id = sess["id"]
                started_at = sess["started_at"]

                # Get all messages from this session (user + assistant only)
                cursor.execute(
                    "SELECT role, content FROM messages "
                    "WHERE session_id = ? AND active = 1 AND role IN ('user', 'assistant') "
                    "ORDER BY id ASC",
                    (session_id,)
                )
                rows = cursor.fetchall()
                if not rows:
                    continue

                full_texts = []
                for r in rows:
                    content = (r["content"] or "").strip()
                    if content:
                        role_label = "用户" if r["role"] == "user" else "助手"
                        full_texts.append(f"[{role_label}]: {content}")

                if not full_texts:
                    continue

                full_convo = "\n".join(full_texts)

                # Truncate: first 500 + last 300 chars
                if len(full_convo) > 800:
                    first_part = full_convo[:500]
                    last_part = full_convo[-300:]
                    preview = first_part + "\n\n... [中间省略] ...\n\n" + last_part
                else:
                    preview = full_convo

                transcripts.append({
                    "session_id": session_id,
                    "started_at": str(started_at) if started_at else "",
                    "message_count": len(rows),
                    "preview": preview,
                })

            return transcripts
        except Exception:
            logger.exception("Error reading session transcripts from state.db")
            return []
        finally:
            conn.close()

    # ── Phase 2: Gather ──────────────────────────────────────────────────

    async def _gather(self, orient: dict) -> list[dict]:
        """Send dream prompt + memory state to auxiliary LLM for analysis."""
        try:
            from agent.auxiliary_client import async_call_llm
        except ImportError:
            logger.warning("agent.auxiliary_client not importable; dream skipped")
            return []

        user_prompt = self._build_dream_user_prompt(orient)
        try:
            response = await async_call_llm(
                task="dream",
                messages=[
                    {"role": "system", "content": DREAM_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
                timeout=60,
            )
        except Exception:
            logger.exception("Dream LLM call failed")
            return []

        content = response.choices[0].message.content
        return self._parse_dream_json(content)

    def _build_dream_user_prompt(self, orient: dict) -> str:
        mem = orient.get("memory_content", "")
        user = orient.get("user_content", "")
        sessions = orient.get("session_transcripts", [])
        parts = [
            "## 当前记忆状态",
            f"字符数: {orient.get('memory_chars_used', 0)} / {orient.get('memory_chars_limit', MEMORY_CHAR_LIMIT)}",
            f"文件数: {orient.get('memory_files', 0)}",
            f"已回顾会话数: {orient.get('sessions_reviewed', 0)}",
            "",
        ]
        if mem:
            truncated = mem[:3000] + ("…" if len(mem) > 3000 else "")
            parts.append(f"### MEMORY.md\n```\n{truncated}\n```")
        if user:
            truncated = user[:1000] + ("…" if len(user) > 1000 else "")
            parts.append(f"### 用户画像\n```\n{truncated}\n```")
        # Append session transcripts
        if sessions:
            parts.append(f"### 最近 {len(sessions)} 个会话转录")
            for i, s in enumerate(sessions, 1):
                parts.append(f"\n#### 会话 {i}: {s['session_id'][-20:]} ({s['message_count']}条消息)")
                parts.append(f"```\n{s['preview']}\n```")
        parts.append("\n请执行 dream consolidation 分析，返回 JSON。")
        return "\n".join(parts)

    def _parse_dream_json(self, raw: str) -> list[dict]:
        """Extract JSON operations from LLM response.

        Also extracts prune_candidates and summary fields into the operation list
        as metadata operations prefixed with _prune_ and _summary for later use.
        """
        try:
            # Try direct JSON
            data = json.loads(raw.strip())
            if isinstance(data, dict):
                ops = data.get("operations", [])
                # Extract prune_candidates and summary as metadata operations
                prunes = data.get("prune_candidates", [])
                summary = data.get("summary", "")
                if prunes:
                    ops.append({"_type": "_prune_candidates", "prune_candidates": prunes})
                if summary:
                    ops.append({"_type": "_summary", "summary": summary})
                return ops
            return []
        except json.JSONDecodeError:
            pass

        # Try to extract JSON block from markdown
        import re
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if match:
            try:
                data = json.loads(match.group(1).strip())
                if isinstance(data, dict):
                    ops = data.get("operations", [])
                    prunes = data.get("prune_candidates", [])
                    summary = data.get("summary", "")
                    if prunes:
                        ops.append({"_type": "_prune_candidates", "prune_candidates": prunes})
                    if summary:
                        ops.append({"_type": "_summary", "summary": summary})
                    return ops
            except json.JSONDecodeError:
                pass

        logger.debug("Dream LLM returned non-JSON: %s", raw[:200])
        return []

    # ── Phase 3: Consolidate ─────────────────────────────────────────────

    def _consolidate(self, operations: list[dict], orient: dict) -> tuple[list[dict], list[dict]]:
        ops, prunes = [], []
        for op in operations:
            op_type = op.get("type", "noop")
            if op_type == "noop":
                continue
            if op_type in {"memory_remove", "fact_remove"}:
                prunes.append(op)
            else:
                ops.append(op)
        return ops, prunes

    # ── Phase 4: Prune ───────────────────────────────────────────────────

    def _prune(self, diff: DreamDiff) -> str:
        op_count = len(diff.operations)
        prune_count = len(diff.prune_candidates)
        if op_count == 0 and prune_count == 0:
            return "Memory tight — no changes needed."
        mem_used = diff.orient_summary.get("memory_chars_used", 0)
        mem_limit = diff.orient_summary.get("memory_chars_limit", MEMORY_CHAR_LIMIT)
        pct = int(mem_used / mem_limit * 100) if mem_limit else 0
        return (
            f"Consolidated {op_count} op(s), {prune_count} prune candidate(s). "
            f"Memory: {mem_used}/{mem_limit} chars ({pct}%)."
        )

    # ── P2: Apply operations to memory and fact_store ────────────────────

    def _apply_operations(self, diff: DreamDiff) -> int:
        """Apply high-confidence (>=0.7) operations to MEMORY.md and fact_store.

        Returns the number of successfully applied operations.
        """
        if not diff.operations:
            return 0

        self._backup_memory()

        applied = 0
        for op in diff.operations:
            confidence = float(op.get("confidence", 0.0))
            if confidence < 0.7:
                logger.debug("Skipping low-confidence operation: %.2f < 0.7", confidence)
                continue

            op_type = op.get("type", "")
            applied += self._apply_single_operation(op_type, op)

        return applied

    def _backup_memory(self) -> None:
        """Create a backup of MEMORY.md before applying changes."""
        memory_path = self._resolve_memory_path()
        if memory_path and os.path.isfile(memory_path):
            backup_path = memory_path + ".dream_backup"
            try:
                import shutil
                shutil.copy2(memory_path, backup_path)
                logger.info("Backed up MEMORY.md to %s", backup_path)
            except OSError:
                logger.exception("Failed to backup MEMORY.md")

    def _resolve_memory_path(self) -> str | None:
        """Find the actual MEMORY.md path."""
        candidates = [
            os.getenv("HERMES_HOME", "/opt/data") + "/memories/MEMORY.md",
        ]
        for p in candidates:
            if os.path.isfile(p):
                return p
        # Fallback: just return the first candidate even if it doesn't exist yet
        return candidates[0]

    def _apply_single_operation(self, op_type: str, op: dict) -> int:
        """Apply a single operation. Returns 1 on success, 0 on skip/failure."""
        if op_type in ("memory_add", "memory_replace", "memory_remove"):
            return self._apply_memory_op(op_type, op)
        elif op_type in ("fact_add", "fact_update", "fact_remove"):
            return self._apply_fact_op(op_type, op)
        return 0

    def _apply_memory_op(self, op_type: str, op: dict) -> int:
        """Apply a memory operation to MEMORY.md using safe_io.atomic_write_text."""
        try:
            from safe_io import atomic_write_text
        except ImportError:
            logger.warning("safe_io.atomic_write_text not available; memory op skipped")
            return 0

        memory_path_str = self._resolve_memory_path()
        if memory_path_str is None:
            logger.warning("Cannot resolve MEMORY.md path")
            return 0
        memory_path = Path(memory_path_str)

        try:
            current = ""
            if os.path.isfile(memory_path):
                with open(memory_path, "r", encoding="utf-8") as f:
                    current = f.read()
        except (OSError, UnicodeDecodeError):
            logger.exception("Failed to read MEMORY.md for modification")
            return 0

        content = op.get("content", "")
        old_text = op.get("old_text", "")

        if op_type == "memory_add":
            new_entry = f"\n- {content.strip()}\n"
            atomic_write_text(memory_path, current + new_entry)
            logger.info("Applied memory_add to %s", memory_path)
            return 1

        elif op_type == "memory_replace":
            if not old_text:
                logger.debug("memory_replace has no old_text; skipping")
                return 0
            if old_text not in current:
                logger.debug("memory_replace: old_text not found in MEMORY.md")
                return 0
            new_current = current.replace(old_text, content, 1)
            atomic_write_text(memory_path, new_current)
            logger.info("Applied memory_replace to %s", memory_path)
            return 1

        elif op_type == "memory_remove":
            if not old_text:
                # If no old_text, treat it as a line match on content
                search = op.get("content", old_text)
                if not search:
                    logger.debug("memory_remove has no search text; skipping")
                    return 0
                lines = current.split("\n")
                filtered = [ln for ln in lines if search not in ln]
                new_current = "\n".join(filtered)
            else:
                if old_text not in current:
                    logger.debug("memory_remove: old_text not found")
                    return 0
                new_current = current.replace(old_text, "", 1)
            atomic_write_text(memory_path, new_current)
            logger.info("Applied memory_remove to %s", memory_path)
            return 1

        return 0

    def _apply_fact_op(self, op_type: str, op: dict) -> int:
        """Apply a fact operation by trying to import and use fact_store module."""
        try:
            from fact_store import add_fact, update_fact, remove_fact
        except ImportError:
            logger.warning("fact_store not importable; fact op skipped (logged)")
            logger.info("Unapplied fact op [%s]: %s", op_type, op.get("content", op.get("entity", "?")))
            return 0

        try:
            entity = op.get("entity", "")
            category = op.get("category", "general")
            content = op.get("content", "")
            trust_delta = float(op.get("trust_delta", 0.0))

            if op_type == "fact_add":
                add_fact(entity=entity, category=category, content=content, trust_delta=trust_delta)
                logger.info("Applied fact_add: %s", entity)
                return 1
            elif op_type == "fact_update":
                update_fact(entity=entity, category=category, content=content, trust_delta=trust_delta)
                logger.info("Applied fact_update: %s", entity)
                return 1
            elif op_type == "fact_remove":
                remove_fact(entity=entity, category=category)
                logger.info("Applied fact_remove: %s", entity)
                return 1
        except Exception:
            logger.exception("Failed to apply fact operation: %s", op_type)

        return 0

    # ── P3: Dream voice adjustment ───────────────────────────────────────

    def _adjust_voice(self, diff: DreamDiff) -> None:
        """Adjust voice from high-confidence dream findings only."""
        try:
            from voice_engine import VoiceEngine
        except ImportError:
            logger.debug("VoiceEngine not available; skipping dream voice adjustment")
            return

        try:
            voice = VoiceEngine()
            applied = 0
            for op in diff.operations:
                confidence = float(op.get("confidence", 0.0))
                if confidence < 0.7:
                    continue
                content = " ".join(str(op.get(k, "")) for k in ("content", "reason", "category", "entity"))
                interest_type = _classify_interest(content)
                if interest_type is None:
                    continue
                voice.on_dream_interest(interest_type, confidence, reason=str(op.get("reason", "")))
                applied += 1
            if applied:
                diff.summary += f" Voice evolved from {applied} high-confidence dream interest(s)."
        except Exception:
            logger.exception("Dream voice adjustment failed")

    # ── Helpers ──────────────────────────────────────────────────────────

    def _read_last_dream_timestamp(self) -> float | None:
        diff = load_latest_diff(self._diff_path)
        if diff and diff.timestamp:
            try:
                return datetime.fromisoformat(diff.timestamp).timestamp()
            except (ValueError, OSError):
                pass
        return None


def _classify_interest(text: str) -> str | None:
    lowered = text.lower()
    academic_terms = (
        "paper", "论文", "研究", "学术", "arxiv", "dataset", "benchmark",
        "实验", "模型", "算法", "theory", "method", "遥感", "remote sensing",
    )
    leisure_terms = (
        "游戏", "电影", "音乐", "bilibili", "视频", "番剧", "小说", "休闲",
        "旅行", "美食", "猫", "v2ex", "小红书", "生活",
    )
    if any(term in lowered for term in academic_terms):
        return "academic"
    if any(term in lowered for term in leisure_terms):
        return "leisure"
    return None
