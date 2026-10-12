"""Compile a text-only action for the qualified public Hermes send interface.

This is NOT an authorization or executable permit. The executor must obtain a
fresh outbox execution grant and bind its host callbacks to the owning profile.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
from typing import Callable, Mapping

from .action_contract import parse_action_contract


class CliSendContractError(ValueError):
    """The public CLI would exceed or alter the requested text action."""


@dataclass(frozen=True, slots=True)
class CliSendPlan:
    profile_id: str = field(repr=False)
    hermes_home: Path = field(repr=False)
    target: str = field(repr=False)
    arguments: tuple[str, ...] = field(repr=False)
    stdin_text: str = field(repr=False)
    message_format: str


def compile_text_cli_plan(
    document: object, route: Mapping, *, profile_id: str, hermes_home: Path,
    resolve_target: Callable, extract_media: Callable, observe_profile_home: Callable,
) -> CliSendPlan:
    """Use only operator-bound profile and actual host parsing callbacks.

    All callbacks are trusted runtime capabilities, not model-selected code.
    They must run under this same profile. Only Markdown intent is supported
    here; actual rendering remains platform-owned and separately qualified.
    Plain-mode forcing and media need different qualified host contracts.
    """
    contract = parse_action_contract(document, capability="hermes.channel.send")
    if not isinstance(route, Mapping) or set(route) != {
            "platform", "profile", "chat_id", "thread_id"}:
        raise CliSendContractError("route descriptor is incomplete or has extra fields")
    if (not isinstance(profile_id, str) or not profile_id or len(profile_id) > 512
            or route["profile"] != profile_id):
        raise CliSendContractError("route belongs to a different profile")
    home = Path(hermes_home)
    if not home.is_absolute() or not home.is_dir():
        raise CliSendContractError("operator profile home must be an existing absolute directory")
    if Path(observe_profile_home()).resolve() != home.resolve():
        raise CliSendContractError("host callbacks are not in the operator-owned profile")
    platform, chat, thread = (route[key] for key in ("platform", "chat_id", "thread_id"))
    if not isinstance(platform, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,63}", platform):
        raise CliSendContractError("platform selector is invalid")
    for name, value in (("chat_id", chat), ("thread_id", thread)):
        if value is None and name == "thread_id":
            continue
        if (not isinstance(value, str) or not value or value != value.strip()
                or len(value) > 512 or any(ord(char) < 32 or ord(char) == 127 for char in value)):
            raise CliSendContractError("destination selector is invalid")
    if chat is None:
        raise CliSendContractError("explicit chat is required; no home-channel fallback")
    text = str(contract.operation["text"])
    text.encode("utf-8")  # No lossy body conversion at the command boundary.
    if "\0" in text:
        raise CliSendContractError("message body contains a null character")
    if contract.operation["format"] != "markdown":
        raise CliSendContractError("public send CLI cannot force plain rendering")
    # Reserve the host protocol namespace even inside quoted examples. An
    # extensionless MEDIA path may become deliverable after filesystem changes;
    # a one-time empty extraction is not proof that later extraction stays empty.
    lowered = text.casefold()
    if ("media:" in lowered or "[[audio_as_voice]]" in lowered
            or "[[as_document]]" in lowered):
        raise CliSendContractError("text action contains reserved media controls")
    media, cleaned = extract_media(text)
    if media or cleaned != text:
        raise CliSendContractError("host parser would alter the text action")
    reference = chat + (":" + thread if thread is not None else "")
    resolved_chat, resolved_thread, error = resolve_target(platform, reference)
    if error or resolved_chat != chat or resolved_thread != thread:
        raise CliSendContractError("host target resolution differs from the authorized route")
    target = platform + ":" + reference
    return CliSendPlan(profile_id, home.resolve(), target,
                       ("send", "--to", target, "--file", "-", "--json"), text, "markdown")
