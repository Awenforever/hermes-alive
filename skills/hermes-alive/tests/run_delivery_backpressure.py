#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "hooks"
sys.path.insert(0, str(HOOKS))
os.environ["HERMES_HOOK_DIR"] = str(HOOKS)

from proactive_watcher import ProactivePlatformWatcher


class Queue:
    def __init__(self, pending: int) -> None:
        self.pending = pending

    def pending_count(self, account_id: str, chat_id: str) -> int:
        return self.pending


class Budget:
    def __init__(self, exhausted: bool, token: str = "token") -> None:
        self.exhausted = exhausted
        self.token = token

    def is_exhausted(self, account_id: str, chat_id: str) -> bool:
        return self.exhausted

    def get_valid_token(self, account_id: str, chat_id: str) -> str:
        return self.token


class Tokens:
    def __init__(self, token: str = "") -> None:
        self.token = token

    def get(self, account_id: str, chat_id: str) -> str:
        return self.token


def adapter(*, pending: int = 0, exhausted: bool = False, token: str = "token"):
    return SimpleNamespace(
        _send_queue=Queue(pending),
        _budget_store=Budget(exhausted, token),
        _token_store=Tokens(token),
        _account_id="acct",
        _send_session=object(),
        _token="transport",
    )


def main() -> int:
    watcher = ProactivePlatformWatcher({}, SimpleNamespace())
    assert watcher._delivery_preflight(adapter(pending=1), "peer") == (
        False,
        "downstream_queue_not_empty",
        1,
    )
    assert watcher._delivery_preflight(adapter(exhausted=True), "peer")[:2] == (
        False,
        "context_token_budget_exhausted",
    )
    assert watcher._delivery_preflight(adapter(token=""), "peer")[:2] == (
        False,
        "context_token_unavailable",
    )
    assert watcher._delivery_preflight(adapter(), "peer") == (
        True,
        "delivery_ready",
        0,
    )
    assert watcher._delivery_preflight(SimpleNamespace(), "peer") == (
        True,
        "preflight_not_applicable",
        0,
    )
    print("HERMES_ALIVE_DELIVERY_BACKPRESSURE_RESULT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
