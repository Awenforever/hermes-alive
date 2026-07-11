"""Non-destructive diff storage for Hermes Dreaming.

All dream results are written as diffs first. The operator reviews the diff
before applying changes to memory and fact_store. This prevents destructive
consolidation from corrupting existing memory.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DreamDiff:
    """A non-destructive dream consolidation diff."""

    dream_version: str = "1.0"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    orient_summary: dict[str, Any] = field(default_factory=dict)
    operations: list[dict[str, Any]] = field(default_factory=list)
    prune_candidates: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    applied: bool = False
    applied_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "dream_version": self.dream_version,
            "timestamp": self.timestamp,
            "orient_summary": self.orient_summary,
            "operations": self.operations,
            "prune_candidates": self.prune_candidates,
            "summary": self.summary,
            "applied": self.applied,
            "applied_at": self.applied_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DreamDiff:
        return cls(
            dream_version=data.get("dream_version", "1.0"),
            timestamp=data.get("timestamp", ""),
            orient_summary=data.get("orient_summary", {}),
            operations=data.get("operations", []),
            prune_candidates=data.get("prune_candidates", []),
            summary=data.get("summary", ""),
            applied=data.get("applied", False),
            applied_at=data.get("applied_at"),
        )

    def has_changes(self) -> bool:
        return bool(self.operations or self.prune_candidates)


def save_diff(diff: DreamDiff, path: str | None = None) -> str:
    """Save a dream diff to a JSON file. Returns the file path."""
    target = path or os.getenv("DREAM_DIFF_PATH", os.path.join(os.getenv("HERMES_HOME", "/opt/data"), "hermes_alive_shared", "dream_diff.json"))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(diff.to_dict(), f, indent=2, ensure_ascii=False)
    return target


def load_latest_diff(path: str | None = None) -> DreamDiff | None:
    """Load the most recent dream diff from disk. Returns None if no diff exists."""
    target = path or os.getenv("DREAM_DIFF_PATH", os.path.join(os.getenv("HERMES_HOME", "/opt/data"), "hermes_alive_shared", "dream_diff.json"))
    if not os.path.exists(target):
        return None
    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    return DreamDiff.from_dict(data)


def mark_applied(path: str | None = None) -> bool:
    """Mark a dream diff as applied. Returns True on success."""
    target = path or os.getenv("DREAM_DIFF_PATH", os.path.join(os.getenv("HERMES_HOME", "/opt/data"), "hermes_alive_shared", "dream_diff.json"))
    diff = load_latest_diff(target)
    if diff is None:
        return False
    diff.applied = True
    diff.applied_at = datetime.now(timezone.utc).isoformat()
    save_diff(diff, target)
    return True


def get_diff_summary(diff: DreamDiff) -> str:
    """Return a human-readable summary of the dream diff."""
    if not diff.has_changes():
        return "No changes — memory is already tight."

    ops = len(diff.operations)
    prunes = len(diff.prune_candidates)
    parts = [f"Dream consolidation: {ops} update(s), {prunes} prune candidate(s)."]
    if diff.summary:
        parts.append(diff.summary)

    for op in diff.operations:
        op_type = op.get("type", "?")
        content = op.get("content", op.get("old_text", ""))
        reason = op.get("reason", "")
        parts.append(f"  [{op_type}] {content[:80]} ({reason[:60]})")

    for pc in diff.prune_candidates:
        reason = pc.get("reason", "")
        parts.append(f"  [prune] {reason[:80]}")

    return "\n".join(parts)
