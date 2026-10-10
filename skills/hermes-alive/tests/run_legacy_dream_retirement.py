#!/usr/bin/env python3
"""Legacy Dream cannot read transcripts or mutate memory, facts, or voice."""

from __future__ import annotations

import asyncio
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile


HOOKS = Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS))

from dream_engine import DreamEngine, RETIRED_REASON  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="alive-retired-dream-") as directory:
        root = Path(directory)
        home = root / "hermes-home"
        memory = home / "memories" / "MEMORY.md"
        memory.parent.mkdir(parents=True)
        memory.write_text("private memory sentinel\n", encoding="utf-8")
        state = home / "state.db"
        with closing(sqlite3.connect(state)) as connection:
            connection.execute("CREATE TABLE private_sentinel(value TEXT)")
            connection.execute(
                "INSERT INTO private_sentinel VALUES (?)",
                ("private conversation sentinel",),
            )
            connection.commit()
        voice = root / "voice.json"
        voice.write_text('{"social_urge": 0.5}', encoding="utf-8")
        diff_path = root / "dream-diff.json"

        old = {key: os.environ.get(key) for key in ("HERMES_HOME", "HERMES_DREAM_ENABLED")}
        try:
            os.environ["HERMES_HOME"] = str(home)
            os.environ["HERMES_DREAM_ENABLED"] = "true"
            engine = DreamEngine(str(diff_path))
            assert engine.should_run() is False
            assert not hasattr(engine, "_orient")
            assert not hasattr(engine, "_apply_operations")
            assert not hasattr(engine, "_adjust_voice")
            diff = asyncio.run(engine.run_dream_cycle())
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        assert diff.operations == [] and diff.prune_candidates == []
        assert diff.applied is False and diff.applied_at is None
        assert diff.summary == RETIRED_REASON
        assert memory.read_text(encoding="utf-8") == "private memory sentinel\n"
        with closing(sqlite3.connect(state)) as connection:
            assert connection.execute("SELECT value FROM private_sentinel").fetchone()[0] == (
                "private conversation sentinel"
            )
        assert json.loads(voice.read_text(encoding="utf-8"))["social_urge"] == 0.5
        receipt = json.loads(diff_path.read_text(encoding="utf-8"))
        assert receipt["operations"] == [] and receipt["applied"] is False
        serialized = diff_path.read_bytes()
        assert b"private memory sentinel" not in serialized
        assert b"private conversation sentinel" not in serialized

    print("HERMES_ALIVE_LEGACY_DREAM_RETIREMENT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
