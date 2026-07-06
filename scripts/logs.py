#!/usr/bin/env python3
"""Query Hermes Alive proactive_log.jsonl with filters.

Usage:
  logs.py                          — show last 10 entries (human-readable)
  logs.py --tail 20                — show last 20 entries
  logs.py --decision sent          — filter by decision type
  logs.py --since 2026-07-05       — entries on or after date
  logs.py --until 2026-07-04       — entries on or before date
  logs.py --reason cooldown        — filter by reason
  logs.py --voice                  — show voice mutation and voice-aware compose/dream entries
  logs.py --preview                — show message_preview for sent entries only
  logs.py --stats                  — count by decision type
  logs.py --json                   — output raw JSON (for piping)
  logs.py --all                    — show all entries (no tail limit)

Examples:
  logs.py --decision sent --since 2026-07-01 --preview
  logs.py --reason cooldown --tail 5
  logs.py --stats --since 2026-07-01
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

DEFAULT_LOG_DIR = os.environ.get("HERMES_ALIVE_SHARED_DIR", "/opt/data/hermes_alive_shared")
DEFAULT_LOG_NAME = "proactive_log.jsonl"


def load_entries(log_dir: Path, log_name: str) -> list[dict]:
    """Load all log entries from current + dated archive files, sorted by time."""
    entries: list[dict] = []

    # Current log
    current = log_dir / log_name
    if current.exists():
        for line in current.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    # Dated archives
    stem = Path(log_name).stem
    suffix = Path(log_name).suffix
    for archive in sorted(log_dir.glob(f"{stem}.*{suffix}")):
        for line in archive.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    # Sort by time field
    entries.sort(key=lambda e: e.get("time", ""))
    return entries


def parse_date(s: str) -> date:
    return datetime.strptime(s.strip(), "%Y-%m-%d").date()


def match_entry(entry: dict, args) -> bool:
    """Check if entry matches all filters."""
    # Decision filter
    if args.decision and entry.get("decision") != args.decision:
        return False

    # Reason filter (substring match)
    if args.reason and args.reason not in entry.get("reason", ""):
        return False

    # Voice filter
    if args.voice:
        if entry.get("decision") == "voice_mutation":
            pass
        elif entry.get("decision") in {"compose", "dream"} and ("voice" in entry or "voice_after" in entry):
            pass
        else:
            return False

    # Time range
    entry_time = entry.get("time", "")
    if args.since or args.until:
        try:
            entry_dt = datetime.fromisoformat(entry_time)
        except (ValueError, TypeError):
            return False

        if args.since:
            since_dt = datetime.combine(parse_date(args.since), datetime.min.time())
            since_dt = since_dt.replace(tzinfo=entry_dt.tzinfo) if entry_dt.tzinfo else since_dt
            if entry_dt < since_dt:
                return False

        if args.until:
            until_dt = datetime.combine(parse_date(args.until), datetime.max.time())
            until_dt = until_dt.replace(tzinfo=entry_dt.tzinfo) if entry_dt.tzinfo else until_dt
            if entry_dt > until_dt:
                return False

    return True


def format_entry(entry: dict, show_preview: bool = False) -> str:
    """Human-readable single entry."""
    time_str = entry.get("time", "?")
    decision = entry.get("decision", "?")
    reason = entry.get("reason", "")
    wid = entry.get("watcher_id", "")[:12]

    parts = [f"[{time_str[:19]}]", f"wid={wid}", f"decision={decision}"]
    if reason:
        parts.append(f"reason={reason}")

    if decision == "sent":
        parts.append(f"type={entry.get('msg_type', '?')}")
        parts.append(f"model={entry.get('generated_by', '?')}")
        parts.append(f"result={entry.get('adapter_result', '?')}")
        msg_index = entry.get("msg_index")
        msg_count = entry.get("msg_count")
        if msg_index is not None and msg_count is not None:
            parts.append(f"[{msg_index}/{msg_count}]")
        if show_preview:
            preview = entry.get("message_preview", "")
            if preview:
                parts.append(f'preview="{preview}"')

    elif decision == "dream":
        parts.append(f"ops={entry.get('ops', 0)}")
        parts.append(f"summary={entry.get('summary', '')}")
        voice_after = entry.get("voice_after", {})
        if voice_after:
            parts.append(f"voice_after={voice_after}")

    elif decision == "discovery":
        parts.append(f"external={entry.get('external_count', 0)}")
        parts.append(f"local={entry.get('local_count', 0)}")
        parts.append(f"sources={entry.get('sources', [])}")

    elif decision == "compose":
        parts.append(f"model={entry.get('model', '?')}")
        parts.append(f"msg_type={entry.get('msg_type', '?')}")
        voice = entry.get('voice', {})
        if voice:
            parts.append(f"voice={voice}")

    elif decision == "voice_mutation":
        parts.append(f"event={entry.get('event', '?')}")
        parts.append(f"delta={entry.get('delta', {})}")
        after = entry.get("after", {})
        if after:
            parts.append(f"after={after}")

    elif decision == "skip":
        parts.append(f"quiet={entry.get('quiet_hours', False)}")

    return "  ".join(parts)


def print_stats(entries: list[dict]):
    """Print summary statistics."""
    counts: dict[str, int] = {}
    reasons: dict[str, int] = {}
    msg_types: dict[str, int] = {}

    for e in entries:
        d = e.get("decision", "unknown")
        counts[d] = counts.get(d, 0) + 1
        r = e.get("reason", "")
        if r:
            reasons[r] = reasons.get(r, 0) + 1
        if d == "sent":
            mt = e.get("msg_type", "unknown")
            msg_types[mt] = msg_types.get(mt, 0) + 1

    print(f"Total entries: {len(entries)}")
    print(f"\nBy decision:")
    for k, v in sorted(counts.items()):
        print(f"  {k:12s} {v:5d}")
    print(f"\nBy reason:")
    for k, v in sorted(reasons.items(), key=lambda x: -x[1])[:10]:
        print(f"  {k:25s} {v:5d}")
    if msg_types:
        print(f"\nSent message types:")
        for k, v in sorted(msg_types.items()):
            print(f"  {k:25s} {v:5d}")


def main():
    parser = argparse.ArgumentParser(description="Query Hermes Alive proactive log")
    parser.add_argument("--tail", type=int, default=10, help="Show last N entries (default 10)")
    parser.add_argument("--decision", choices=["sent", "skip", "dream", "discovery", "compose", "voice_mutation", "start", "stop", "error"], help="Filter by decision")
    parser.add_argument("--since", help="Entries on or after YYYY-MM-DD")
    parser.add_argument("--until", help="Entries on or before YYYY-MM-DD")
    parser.add_argument("--reason", help="Filter by reason (substring match)")
    parser.add_argument("--voice", action="store_true", help="Show voice mutation and voice-aware compose/dream entries")
    parser.add_argument("--preview", action="store_true", help="Show message preview for sent entries")
    parser.add_argument("--stats", action="store_true", help="Show summary statistics")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    parser.add_argument("--all", action="store_true", help="Show all entries (no tail limit)")
    parser.add_argument("--dir", default=DEFAULT_LOG_DIR, help=f"Log directory (default: {DEFAULT_LOG_DIR})")
    args = parser.parse_args()

    log_dir = Path(args.dir)
    entries = load_entries(log_dir, DEFAULT_LOG_NAME)

    # Apply filters
    filtered = [e for e in entries if match_entry(e, args)]

    if args.stats:
        print_stats(filtered)
        return

    if args.json:
        print(json.dumps(filtered, ensure_ascii=False, indent=2))
        return

    # Tail
    limit = None if args.all else args.tail
    display = filtered if limit is None else filtered[-limit:]

    for entry in display:
        print(format_entry(entry, show_preview=args.preview))


if __name__ == "__main__":
    main()
