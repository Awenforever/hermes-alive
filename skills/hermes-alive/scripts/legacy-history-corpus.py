#!/usr/bin/env python3
"""Read-only, content-free legacy-log export; never an outcome-learning import."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import secrets
import shlex
import subprocess
import sys

DECISIONS = frozenset({
    "activity_guard", "circadian_sleep_quiet_enforcement", "compose", "compose_rejected",
    "content_delivery", "content_delivery_skipped", "delivery_circuit_closed",
    "delivery_circuit_open", "delivery_plan", "discovery", "dream", "editorial_review",
    "error", "manual_discovery", "manual_discovery_override", "peer_resolution", "policy",
    "policy_deferred", "proactive_quality_candidate_shadow", "proactive_quality_shadow",
    "semantic_bubble_plan", "sent", "skip", "start", "stop", "topic_dedup_committed",
    "topic_dedup_released", "topic_dedup_reservation", "circadian_enforcement",
    "circadian_shadow", "sleep_quiet_policy_enforcement", "sleep_quiet_policy_shadow",
    "voice_mutation",
})
BOOL_FIELDS = (
    "context_token_present", "session_busy_boolean", "behavior_changed", "watcher_enforced",
    "quality_enforcement", "circadian_sleep_enforcement", "content_delivered", "fallback_used",
)
COUNT_FIELDS = ("msg_count", "msg_index", "discovery_items", "context_queue_message_count",
                "context_queue_distinct_session_count", "context_prompt_eligible_count")
AGE_FIELDS = ("latest_context_age_seconds", "context_queue_db_lag_seconds")
LABEL_NAMES = ("useful", "interruption_regret", "factual_error", "user_control_violation",
               "delivery_succeeded", "task_completed")


def timestamp(value):
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed.astimezone(timezone.utc).isoformat()
    except (ValueError, OverflowError):
        return None


def pseudonym(key, domain, value):
    if not isinstance(value, str) or not value or len(value) > 4096:
        return None
    digest = hmac.new(key, (domain + "\0" + value).encode(), hashlib.sha256).hexdigest()
    return domain + ":" + digest[:32]


def sanitize(row, *, key, source_index, line_index):
    # Deliberate allowlist: no arbitrary strings/nested payloads or raw hashes.
    decision = row.get("decision")
    decision = decision if isinstance(decision, str) and decision in DECISIONS else "other"
    counts = {name: value if type(value) is int and 0 <= value <= 1_000_000 else None
              for name in COUNT_FIELDS for value in (row.get(name),)}
    ages = {name: value if type(value) in (int, float) and 0 <= value <= 1_000_000_000
            and math.isfinite(value) else None
            for name in AGE_FIELDS for value in (row.get(name),)}
    return {
        "record_id": f"legacy-record:{source_index}:{line_index}",
        "observed_at": timestamp(row.get("time")),
        "watcher_started_at": timestamp(row.get("started_at")),
        "watcher_ref": pseudonym(key, "watcher", row.get("watcher_id")),
        "tick_ref": pseudonym(key, "tick", row.get("tick_id")),
        "model_ref": pseudonym(key, "model", row.get("model")),
        "decision_class": decision,
        "decision_ref": pseudonym(key, "decision", row.get("decision")),
        "reported_flags": {name: row.get(name) if type(row.get(name)) is bool else None
                           for name in BOOL_FIELDS},
        "reported_counts": counts,
        "reported_ages_seconds": ages,
        "delivery_claim": "legacy_sent_report" if decision == "sent" else None,
        "labels": {name: None for name in LABEL_NAMES},
    }


def export(paths, *, max_bytes=16 * 1024 * 1024):
    if len(paths) > 32:
        raise ValueError("too many snapshot sources")
    key = secrets.token_bytes(32)  # Per-export, never persisted or published.
    records, sources, identities = [], [], set()
    invalid = total_bytes = 0
    for source_index, path in enumerate(paths):
        with Path(path).open("rb") as stream:
            before = os.fstat(stream.fileno())
            identity = (before.st_dev, before.st_ino)
            if identity in identities:
                raise ValueError("duplicate snapshot source")
            identities.add(identity)
            if before.st_size > max_bytes:
                raise ValueError("source exceeds snapshot size limit")
            total_bytes += before.st_size
            if total_bytes > 64 * 1024 * 1024:
                raise ValueError("combined sources exceed snapshot size limit")
            raw = stream.read(before.st_size)
            after = os.fstat(stream.fileno())
        if len(raw) != before.st_size or after.st_size < before.st_size:
            raise ValueError("source changed by truncation during snapshot")
        sources.append({"source_index": source_index, "snapshot_bytes": len(raw),
                        "append_observed": after.st_size > before.st_size,
                        "snapshot_ref": hmac.new(key, raw, hashlib.sha256).hexdigest()})
        for line_index, line in enumerate(raw.splitlines(), start=1):
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError()
            except (ValueError, UnicodeError, RecursionError):
                invalid += 1
                continue
            records.append(sanitize(row, key=key, source_index=source_index, line_index=line_index))
            if len(records) > 100_000:
                raise ValueError("snapshot record limit exceeded")
    decisions = Counter(record["decision_class"] for record in records)
    previous, regressions = None, 0
    for record in records:
        current = record["observed_at"]
        if current is not None:
            regressions += bool(previous is not None and current < previous)
            previous = current
    return {"schema_version": 1, "corpus_id": "legacy-corpus:" + secrets.token_hex(16),
            "corpus_kind": "legacy_structural_observations",
            "order": "caller_source_order_then_line_order_not_causal_order",
            "qualification": "structural_only_no_reward_or_policy_superiority_claim",
            "sources": sources, "records": records,
            "summary": {"records": len(records), "invalid_lines": invalid,
                        "decisions": dict(sorted(decisions.items())),
                        "valid_timestamps": sum(r["observed_at"] is not None for r in records),
                        "unknown_decision_groups": len({r["decision_ref"] for r in records
                            if r["decision_class"] == "other" and r["decision_ref"] is not None}),
                        "time_regressions_in_source_order": regressions,
                        "labelled_outcomes": 0}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    # Keep remote POSIX paths unchanged on a Windows caller.
    parser.add_argument("--input", nargs="+", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-bytes", type=int, default=16 * 1024 * 1024)
    parser.add_argument("--remote-ssh")
    parser.add_argument("--container")
    parser.add_argument("--remote-python", default="python3")
    args = parser.parse_args()
    if not 0 < args.max_bytes <= 64 * 1024 * 1024:
        raise ValueError("invalid snapshot size bound")
    if args.remote_ssh:
        if args.remote_ssh.startswith("-") or not args.container or args.container.startswith("-"):
            raise ValueError("explicit SSH target and container are required")
        command = ["docker", "exec", "-i", args.container, args.remote_python, "-B", "-",
                   "--input", *map(str, args.input), "--max-bytes", str(args.max_bytes)]
        result = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
                                 args.remote_ssh, shlex.join(command)],
                                input=Path(__file__).read_text(encoding="utf-8"),
                                capture_output=True, text=True, timeout=90)
        if result.returncode:
            # Remote errors are not a reason to copy raw source logs locally.
            raise RuntimeError("read-only remote structural export failed")
        corpus = json.loads(result.stdout)
    else:
        corpus = export(args.input, max_bytes=args.max_bytes)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(corpus, stream, ensure_ascii=False, sort_keys=True, allow_nan=False)
        print(json.dumps(corpus["summary"], sort_keys=True))
    else:
        print(json.dumps(corpus, ensure_ascii=False, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
