"""Register Alive's structural tool observer against Hermes' native plugin API."""

from __future__ import annotations

import importlib
import importlib.util
import hashlib
import logging
import os
from pathlib import Path
import sys
from functools import lru_cache
from typing import Any


logger = logging.getLogger(__name__)


def _shared_dir() -> Path:
    configured = os.getenv("HERMES_ALIVE_SHARED_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    from hermes_constants import get_hermes_home

    return get_hermes_home() / "plugin-data" / "hermes-alive" / "runtime"


@lru_cache(maxsize=1)
def _kernel_module():
    """Load this exact kernel build without mutating global ``sys.path``.

    The content-derived package name prevents an in-process plugin refresh from
    silently reusing modules from the previous checkout.
    """

    root = (
        Path(__file__).resolve().parent
        / "skills"
        / "hermes-alive"
        / "hooks"
        / "alive_kernel"
    )
    digest = hashlib.sha256()
    for source in sorted(root.glob("*.py")):
        digest.update(source.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
    package_name = f"hermes_alive_embedded_kernel_{digest.hexdigest()[:16]}"
    package = sys.modules.get(package_name)
    if package is None:
        spec = importlib.util.spec_from_file_location(
            package_name,
            root / "__init__.py",
            submodule_search_locations=[str(root)],
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("Hermes Alive embedded kernel is unavailable")
        package = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = package
        try:
            spec.loader.exec_module(package)
        except Exception:
            sys.modules.pop(package_name, None)
            raise
    return importlib.import_module(f"{package_name}.tool_receipts")


def _shadow_enabled() -> bool:
    return os.getenv("HERMES_ALIVE_KERNEL_SHADOW_ENABLED", "false").strip().lower() in {
        "1", "true", "yes", "on",
    }


def on_post_tool_call(**values: Any) -> None:
    """Fail-open observer; never log arguments, results or error messages."""

    if not _shadow_enabled():
        return
    try:
        _kernel_module().record_post_tool_call(_shared_dir(), values)
    except Exception as exc:
        logger.warning(
            "Hermes Alive structural tool receipt was not recorded: %s", type(exc).__name__
        )


def register_tool_receipt_hook(ctx: Any) -> None:
    ctx.register_hook("post_tool_call", on_post_tool_call)
