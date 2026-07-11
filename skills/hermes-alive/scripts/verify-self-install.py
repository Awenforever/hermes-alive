#!/usr/bin/env python3
"""Compatibility wrapper for the lifecycle verifier."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

def main() -> int:
    lifecycle = Path(__file__).resolve().with_name("hermes-alive-lifecycle.py")
    result = subprocess.run(
        [sys.executable, str(lifecycle), "verify"],
        check=False,
    )
    print(
        "VERIFY_SELF_INSTALL_RESULT=PASS"
        if result.returncode == 0
        else "VERIFY_SELF_INSTALL_RESULT=FAIL"
    )
    return result.returncode

if __name__ == "__main__":
    raise SystemExit(main())
