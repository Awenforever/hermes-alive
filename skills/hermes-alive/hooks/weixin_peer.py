"""Resolve the canonical Weixin peer used by sessions and context tokens.

The iLink QR credential identifies the bot account, while inbound DM sessions and
context tokens are keyed by the human peer. Hermes Alive accepts an explicitly
configured chat ID, but normalizes it to a context-bearing peer when that choice
is unambiguous.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


CHAT_ENV = "HERMES_PROACTIVE_WEIXIN_CHAT_ID"
ACCOUNT_ENV = "WEIXIN_ACCOUNT_ID"


def hermes_home() -> Path:
    return Path(os.getenv("HERMES_HOME", "/opt/data"))


def _account_id(explicit: str | None = None) -> str:
    value = explicit if explicit is not None else os.getenv(ACCOUNT_ENV, "")
    return str(value or "").strip()


def _token_store_path(
    *,
    home: Path | None = None,
    account_id: str | None = None,
) -> Path | None:
    root = home or hermes_home()
    account = _account_id(account_id)
    accounts = root / "weixin" / "accounts"

    if account:
        return accounts / f"{account}.context-tokens.json"

    candidates = sorted(accounts.glob("*.context-tokens.json"))
    if len(candidates) == 1:
        return candidates[0]

    return None


def context_token_peers(
    *,
    home: Path | None = None,
    account_id: str | None = None,
) -> list[str]:
    path = _token_store_path(home=home, account_id=account_id)
    if path is None or not path.is_file():
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(payload, dict):
        return []

    peers: list[str] = []
    for raw_peer, raw_token in payload.items():
        peer = str(raw_peer or "").strip()
        token = str(raw_token or "").strip()
        if peer and token:
            peers.append(peer)

    return sorted(set(peers))


def latest_weixin_session_peer(
    *,
    home: Path | None = None,
    allowed_peers: set[str] | None = None,
) -> str | None:
    root = home or hermes_home()
    db_path = Path(
        os.getenv(
            "HERMES_STATE_DB",
            str(root / "state.db"),
        )
    )
    if not db_path.is_file():
        return None

    try:
        conn = sqlite3.connect(str(db_path), timeout=2)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT user_id
                FROM sessions
                WHERE source = 'weixin'
                  AND user_id IS NOT NULL
                  AND TRIM(user_id) != ''
                ORDER BY COALESCE(
                    ended_at,
                    started_at,
                    0
                ) DESC
                LIMIT 20
                """
            ).fetchall()
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        return None

    for row in rows:
        peer = str(row["user_id"] or "").strip()
        if not peer:
            continue
        if allowed_peers is None or peer in allowed_peers:
            return peer

    return None


def _suffix_candidates(configured: str) -> list[str]:
    candidates: list[str] = []
    for suffix in ("@im.wechat", "@im.bot"):
        if configured.endswith(suffix):
            candidate = configured[: -len(suffix)].strip()
            if candidate:
                candidates.append(candidate)
    return candidates


def resolve_weixin_peer(
    configured_chat_id: str | None = None,
    *,
    home: Path | None = None,
    account_id: str | None = None,
) -> tuple[str, str]:
    configured = str(
        configured_chat_id
        if configured_chat_id is not None
        else os.getenv(CHAT_ENV, "")
    ).strip()

    peers = context_token_peers(
        home=home,
        account_id=account_id,
    )
    peer_set = set(peers)

    if configured and configured in peer_set:
        return configured, "exact_context_peer"

    for candidate in _suffix_candidates(configured):
        if candidate in peer_set:
            return candidate, "stripped_platform_suffix"

    latest = latest_weixin_session_peer(
        home=home,
        allowed_peers=peer_set or None,
    )
    if latest is not None:
        return latest, "latest_weixin_session_peer"

    if len(peers) == 1:
        return peers[0], "single_context_peer"

    if configured:
        return configured, "configured_unresolved"

    return "", "unavailable"


def normalize_weixin_chat_env(
    *,
    home: Path | None = None,
    account_id: str | None = None,
) -> tuple[str, str]:
    configured = os.getenv(CHAT_ENV, "").strip()
    resolved, reason = resolve_weixin_peer(
        configured,
        home=home,
        account_id=account_id,
    )
    if resolved:
        os.environ[CHAT_ENV] = resolved
    return resolved, reason


def adapter_context_token_present(
    adapter: Any,
    chat_id: str,
) -> bool:
    account_id = str(
        getattr(adapter, "_account_id", "") or ""
    ).strip()
    store = getattr(adapter, "_token_store", None)
    if not account_id or store is None or not hasattr(store, "get"):
        return False

    try:
        return bool(store.get(account_id, str(chat_id)))
    except Exception:
        return False
