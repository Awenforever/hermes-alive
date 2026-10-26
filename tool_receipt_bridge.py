"""Register Alive's structural tool observer against Hermes' native plugin API."""

from __future__ import annotations

import importlib
import importlib.util
from importlib.machinery import ModuleSpec
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


@lru_cache(maxsize=2)
def _kernel_module(module_name="tool_receipts"):
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
        # Observers need their relative dependencies, not the convenience
        # facade that imports every subsystem (including installed-hook-only
        # recovery helpers). A namespace isolates this build without executing
        # unrelated startup code or borrowing another checkout's sys.path.
        spec = ModuleSpec(package_name, loader=None, is_package=True)
        spec.submodule_search_locations = [str(root)]
        package = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = package
    if module_name not in {"tool_receipts", "admitted_inbound", "core_shadow_assembly", "kernel_setup"}:
        raise ValueError("unknown embedded observer module")
    return importlib.import_module(f"{package_name}.{module_name}")


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


def register_tool_receipt_hook(ctx: Any, binding=None) -> None:
    if binding is None:
        ctx.register_hook('post_tool_call',on_post_tool_call)
        return

    def observe(**values):
        if binding.closed:return
        try:
            from .gateway_session_bridge import SessionScopeUnavailable
            from .kernel_execution_bridge import runtime_engine,configured_owner,ConfiguredOwnerMismatch
            if runtime_engine(binding)!='kernel':
                return on_post_tool_call(**values)
            binding._require_home()
            continuity=binding._continuity
            if continuity is None:return
            from gateway.session_context import get_session_env
            scope=continuity.router.scope_for_hook(dict(session_id=values.get('session_id'),
                sender_id=get_session_env('HERMES_SESSION_USER_ID'),
                platform=get_session_env('HERMES_SESSION_PLATFORM')))
            if scope is None:return
            try:store,configured=configured_owner(binding,scope)
            except ConfiguredOwnerMismatch:return
            if configured.options.get('observe_core_tools') is not True:return
            _kernel_module().ToolReceiptRecorder.for_configured_owner(store,configured).record(values)
        except SessionScopeUnavailable:
            return
        except Exception as exc:
            logger.warning('Alive configured tool observation unavailable: %s',type(exc).__name__)
        # Observability never consumes input, changes tool results or grants IO.
    ctx.register_hook('post_tool_call',observe)
