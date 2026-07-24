#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath


REQUIRED = [
    "README.md",
    "README_CN.md",
    "LICENSE",
    "VERSION",
    "SECURITY.md",
    "CONTRIBUTING.md",
    ".gitignore",
    ".github/workflows/ci.yml",
    "ci/requirements.txt",
    "ci/fakes/agent/__init__.py",
    "ci/fakes/agent/auxiliary_client.py",
    "metadata/hermes-alive.json",
    "metadata/hermes-alive-source.sha256",
    "scripts/bootstrap.sh",
    "scripts/portable-ci.sh",
    "scripts/verify-repository.py",
    "skills/hermes-alive/SKILL.md",
    "skills/hermes-alive/README.md",
    "skills/hermes-alive/README_CN.md",
    "skills/hermes-alive/scripts/install.sh",
    "skills/hermes-alive/scripts/verify.sh",
    "skills/hermes-alive/scripts/uninstall.sh",
    "skills/hermes-alive/tests/run_all.sh",
    "REPOSITORY_MANIFEST.sha256",
]

ALLOWED_ENV = {
    "skills/hermes-alive/templates/.env.template",
}

DOCS = [
    "README.md",
    "README_CN.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    "skills/hermes-alive/README.md",
    "skills/hermes-alive/README_CN.md",
    "skills/hermes-alive/SKILL.md",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_manifest(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        digest, rel = raw.split("  ", 1)
        values[rel.removeprefix("./")] = digest
    return values


def markdown_links(text: str) -> list[str]:
    return re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--report")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    errors: list[str] = []

    for rel in REQUIRED:
        if not (root / rel).is_file():
            errors.append(f"missing:{rel}")

    metadata_path = root / "metadata/hermes-alive.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    version = (root / "VERSION").read_text(encoding="utf-8").strip()

    skill_text = (root / "skills/hermes-alive/SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"^version:\s*([^\s]+)\s*$", skill_text, re.MULTILINE)
    skill_version = match.group(1) if match else ""

    if version != "2.4.2":
        errors.append(f"unexpected_version:{version}")
    if metadata.get("version") != version:
        errors.append("metadata_version_mismatch")
    if skill_version != version:
        errors.append(f"skill_version_mismatch:{skill_version}")
    if metadata.get("skill_path") != "skills/hermes-alive":
        errors.append("metadata_skill_path")
    if metadata.get("repository_stage") != "candidate":
        errors.append("metadata_stage")
    if metadata.get("production_deployed") is not False:
        errors.append("production_deployed_claim")
    if metadata.get("real_wechat_e2e_completed") is not False:
        errors.append("real_wechat_claim")

    for rel in DOCS:
        path = root / rel
        for link in markdown_links(path.read_text(encoding="utf-8")):
            if link.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = link.split("#", 1)[0]
            if not target:
                continue
            resolved = (path.parent / target).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                errors.append(f"link_outside_root:{rel}:{link}")
                continue
            if not resolved.exists():
                errors.append(f"broken_link:{rel}:{link}")

    source_manifest = parse_manifest(root / "metadata/hermes-alive-source.sha256")
    skill_root = root / "skills/hermes-alive"
    for rel, digest in source_manifest.items():
        path = skill_root / rel
        if not path.is_file():
            errors.append(f"source_manifest_missing:{rel}")
        elif sha256(path) != digest:
            errors.append(f"source_manifest_mismatch:{rel}")

    repository_manifest = parse_manifest(root / "REPOSITORY_MANIFEST.sha256")
    for rel, digest in repository_manifest.items():
        path = root / rel
        if not path.is_file():
            errors.append(f"repository_manifest_missing:{rel}")
        elif sha256(path) != digest:
            errors.append(f"repository_manifest_mismatch:{rel}")

    actual_manifest_files = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and ".git" not in path.relative_to(root).parts
        and path.name != "REPOSITORY_MANIFEST.sha256"
    }
    if actual_manifest_files != set(repository_manifest):
        missing = sorted(actual_manifest_files - set(repository_manifest))
        extra = sorted(set(repository_manifest) - actual_manifest_files)
        errors.append(f"repository_manifest_set:missing={missing}:extra={extra}")

    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        if ".git" in path.relative_to(root).parts:
            continue
        if path.is_dir() and path.name == "__pycache__":
            errors.append(f"pycache:{rel}")
        if path.is_file() and path.suffix in {".pyc", ".pyo"}:
            errors.append(f"compiled_python:{rel}")
        if path.is_file() and path.name.startswith(".env") and rel not in ALLOWED_ENV:
            errors.append(f"env_artifact:{rel}")
        mode = stat.S_IMODE(path.stat().st_mode)
        if path.is_dir() and mode != 0o755:
            errors.append(f"directory_mode:{rel}:{oct(mode)}")
        if path.is_file():
            expected = 0o755 if os.access(path, os.X_OK) else 0o644
            if mode != expected:
                errors.append(f"file_mode:{rel}:{oct(mode)}:{oct(expected)}")

    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for required in (
        "actions/checkout@v6",
        "actions/setup-python@v6",
        'python-version: "3.13"',
        "permissions:",
        "contents: read",
        "bash scripts/portable-ci.sh",
    ):
        if required not in workflow:
            errors.append(f"workflow_missing:{required}")

    payload = {
        "result": "PASS" if not errors else "FAIL",
        "errors": errors,
        "version": version,
        "skill_version": skill_version,
        "source_manifest_entries": len(source_manifest),
        "repository_manifest_entries": len(repository_manifest),
    }

    if args.report:
        Path(args.report).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if errors:
        for error in errors:
            print(error)
        return 1

    print("HERMES_ALIVE_REPOSITORY_VERIFY_RESULT=PASS")
    print(f"version={version}")
    print(f"source_manifest_entries={len(source_manifest)}")
    print(f"repository_manifest_entries={len(repository_manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
