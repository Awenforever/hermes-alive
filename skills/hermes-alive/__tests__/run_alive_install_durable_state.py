#!/usr/bin/env python3
"""Local synthetic state-probe checks, not real package-install qualification."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main() -> int:
    tests = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix="alive-admission-durable-") as directory:
        root = Path(directory)
        profile = root / "profile"
        shutil.copytree(tests.parent / "hooks", profile / "skills" / "hermes-alive" / "hooks",
                        ignore=shutil.ignore_patterns("__pycache__"))
        env = dict(os.environ, HERMES_HOME=str(profile), PYTHONDONTWRITEBYTECODE="1")
        def probe(mode):
            return subprocess.run(
                [sys.executable, "-B", str(tests / "admission_state_fixture.py"), mode,
                 "--profile", str(profile), "--expected", str(root / "baseline.json")],
                env=env, capture_output=True, text=True, timeout=60,
            )
        created = probe("create")
        assert created.returncode == 0, created.stderr
        checked = probe("check")
        assert checked.returncode == 0, checked.stderr
        key = profile / "plugin-data" / "hermes-alive" / "runtime" / "kernel" / "content-vault" / "content.key"
        original = key.read_bytes()
        key.unlink()
        missing = probe("check")
        assert missing.returncode != 0 and "durable fixture state was lost" in missing.stderr
        assert not key.exists(), "a verification read replaced the missing key"
        key.write_bytes(original)
        assert probe("check").returncode == 0
        key.write_bytes(b"synthetic-invalid-replacement-key")
        assert probe("check").returncode != 0
        key.write_bytes(original)
        assert probe("check").returncode == 0
        assert probe("create").returncode != 0, "baseline could be silently overwritten"
    print("HERMES_ALIVE_INSTALL_DURABLE_STATE_CONTRACT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
