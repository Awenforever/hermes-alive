#!/usr/bin/env python3
"""Regenerate transport manifests from canonical staged Git blobs.

Reading the index instead of the checkout makes hashes independent of host
line-ending conversion. Stage intended changes before running this script.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def tracked_files() -> list[str]:
    return sorted(
        value.decode("utf-8", errors="surrogateescape")
        for value in git("ls-files", "-z").split(b"\0")
        if value
    )


def staged_blob(path: str) -> bytes:
    return git("show", f":{path}")


def digest(path: str) -> str:
    return hashlib.sha256(staged_blob(path)).hexdigest()


def write(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    files = tracked_files()
    skill_prefix = "skills/hermes-alive/"
    source = [
        f"{digest(path)}  ./{path.removeprefix(skill_prefix)}"
        for path in files
        if path.startswith(skill_prefix)
    ]
    write(ROOT / "metadata/hermes-alive-source.sha256", source)

    # The repository manifest includes the newly written source manifest. Stage
    # it so the repository digest also comes from a canonical index blob.
    subprocess.check_call(
        ["git", "-C", str(ROOT), "add", "metadata/hermes-alive-source.sha256"]
    )
    repository = [
        f"{digest(path)}  ./{path}"
        for path in tracked_files()
        if path != "REPOSITORY_MANIFEST.sha256"
    ]
    write(ROOT / "REPOSITORY_MANIFEST.sha256", repository)
    print("HERMES_ALIVE_MANIFEST_UPDATE_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
