#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path


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


def git_command(root: Path, *args: str) -> list[str]:
    # A repository mounted read-only into an isolated container can have a
    # different numeric owner from the container user. Use an exact,
    # per-command safe.directory exception for this repository only.
    return [
        "git",
        "-c",
        f"safe.directory={root}",
        "-C",
        str(root),
        *args,
    ]


def git_worktree(root: Path) -> bool:
    probe = subprocess.run(
        git_command(root, "rev-parse", "--is-inside-work-tree"),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return probe.returncode == 0 and probe.stdout.strip() == "true"


def git_index_modes(root: Path) -> dict[str, str]:
    output = subprocess.check_output(
        git_command(root, "ls-files", "--stage", "-z")
    )
    modes: dict[str, str] = {}
    for record in output.split(b"\0"):
        if not record:
            continue
        metadata, raw_path = record.split(b"\t", 1)
        mode, _object_id, stage = metadata.decode("ascii").split(" ", 2)
        path = raw_path.decode("utf-8", errors="surrogateescape")
        if stage != "0":
            raise RuntimeError(f"unmerged index entry: {path}")
        modes[path] = mode
    return modes


def validate_permissions(
    root: Path,
    actual_files: set[str],
    errors: list[str],
    warnings: list[str],
) -> str:
    if not git_worktree(root):
        for path in root.rglob("*"):
            rel = path.relative_to(root).as_posix()
            if ".git" in path.relative_to(root).parts:
                continue
            if path.is_symlink():
                errors.append(f"symlink_not_allowed:{rel}")
                continue
            mode = stat.S_IMODE(path.stat().st_mode)
            if mode & 0o7000:
                errors.append(f"special_mode:{rel}:{oct(mode)}")
            if path.is_dir() and mode != 0o755:
                errors.append(f"directory_mode:{rel}:{oct(mode)}")
            if path.is_file():
                expected = 0o755 if os.access(path, os.X_OK) else 0o644
                if mode != expected:
                    errors.append(
                        f"file_mode:{rel}:{oct(mode)}:{oct(expected)}"
                    )
        return "exact_pre_git_modes"

    try:
        index_modes = git_index_modes(root)
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        errors.append(f"git_index_modes:{type(exc).__name__}:{exc}")
        return "git_index_unavailable"

    tracked = set(index_modes)
    expected_tracked = set(actual_files)
    expected_tracked.add("REPOSITORY_MANIFEST.sha256")
    if tracked != expected_tracked:
        missing = sorted(expected_tracked - tracked)
        extra = sorted(tracked - expected_tracked)
        errors.append(f"git_tracked_set:missing={missing}:extra={extra}")

    for rel, git_mode in sorted(index_modes.items()):
        path = root / rel
        if git_mode not in {"100644", "100755"}:
            errors.append(f"unsupported_git_mode:{rel}:{git_mode}")
            continue
        if not path.is_file() or path.is_symlink():
            errors.append(f"tracked_regular_file_missing:{rel}")
            continue

        # Git transports only the regular-file type and executable bit:
        # 100644 or 100755. The checkout filesystem may materialize broader
        # read/write/execute or special bits (for example 0666, 0777, 2755).
        # Those bits are host policy, not Git-object data, so record them only
        # as environment warnings.
        materialized = stat.S_IMODE(path.stat().st_mode)
        canonical = 0o755 if git_mode == "100755" else 0o644
        if materialized != canonical:
            warnings.append(
                f"materialized_mode_noncanonical:{rel}:"
                f"{oct(materialized)}:{oct(canonical)}"
            )

    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        if ".git" in path.relative_to(root).parts:
            continue
        if path.is_dir():
            if path.is_symlink():
                errors.append(f"directory_symlink_not_allowed:{rel}")
                continue
            mode = stat.S_IMODE(path.stat().st_mode)
            # Git does not store directory entries or directory modes.
            # The full materialized directory mode is checkout-host policy.
            if mode != 0o755:
                warnings.append(
                    f"materialized_directory_mode_noncanonical:"
                    f"{rel}:{oct(mode)}:0o755"
                )

    return "git_index_executable_bits"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--report")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    for rel in REQUIRED:
        if not (root / rel).is_file():
            errors.append(f"missing:{rel}")

    metadata_path = root / "metadata/hermes-alive.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    version = (root / "VERSION").read_text(encoding="utf-8").strip()

    skill_text = (root / "skills/hermes-alive/SKILL.md").read_text(
        encoding="utf-8"
    )
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

    source_manifest = parse_manifest(
        root / "metadata/hermes-alive-source.sha256"
    )
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
        errors.append(
            f"repository_manifest_set:missing={missing}:extra={extra}"
        )

    for path in root.rglob("*"):
        rel = path.relative_to(root).as_posix()
        if ".git" in path.relative_to(root).parts:
            continue
        if path.is_dir() and path.name == "__pycache__":
            errors.append(f"pycache:{rel}")
        if path.is_file() and path.suffix in {".pyc", ".pyo"}:
            errors.append(f"compiled_python:{rel}")
        if (
            path.is_file()
            and path.name.startswith(".env")
            and rel not in ALLOWED_ENV
        ):
            errors.append(f"env_artifact:{rel}")

    permission_validation = validate_permissions(
        root, actual_manifest_files, errors, warnings
    )

    workflow = (root / ".github/workflows/ci.yml").read_text(
        encoding="utf-8"
    )
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
        "warnings": warnings,
        "version": version,
        "skill_version": skill_version,
        "source_manifest_entries": len(source_manifest),
        "repository_manifest_entries": len(repository_manifest),
        "permission_validation": permission_validation,
        "noncanonical_materialized_modes": len(warnings),
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
    print(f"permission_validation={permission_validation}")
    print(f"noncanonical_materialized_modes={len(warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
