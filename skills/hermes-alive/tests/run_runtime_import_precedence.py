#!/usr/bin/env python3
"""Regression: the active hook must outrank a stale plugin checkout."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"

with tempfile.TemporaryDirectory(prefix="alive-stale-plugin-") as temporary:
    stale = Path(temporary)
    (stale / "proactive_watcher.py").write_text(
        "SOURCE = 'stale-plugin'\n",
        encoding="utf-8",
    )

    hook_text = str(HOOKS)
    sys.path[:] = [entry for entry in sys.path if entry != hook_text]
    sys.path.insert(0, str(stale))
    sys.path.append(hook_text)
    sys.modules.pop("proactive_watcher", None)

    spec = importlib.util.spec_from_file_location(
        "alive_handler_import_precedence_test",
        HOOKS / "handler.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert Path(sys.path[0]).resolve() == HOOKS.resolve(), sys.path[:4]
    resolved = importlib.util.find_spec("proactive_watcher")
    assert resolved and resolved.origin
    assert Path(resolved.origin).resolve() == (HOOKS / "proactive_watcher.py").resolve()

print("HERMES_ALIVE_RUNTIME_IMPORT_PRECEDENCE_RESULT=PASS")
