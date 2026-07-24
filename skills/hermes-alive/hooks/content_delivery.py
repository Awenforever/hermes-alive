# Hermes Alive structured rich-content delivery.
# Marker: RICH_CONTENT_DELIVERY_V1
# Marker: RICH_CONTENT_CAPABILITY_FALLBACK_V1
# Marker: RICH_CONTENT_METADATA_V1
# Marker: RICH_CONTENT_REFERENCE_V1
# Marker: RICH_CONTENT_MODEL_ATTRIBUTION_V2

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


CONTENT_REF_RE = re.compile(
    r"\[\[CONTENT_REF:([A-Za-z0-9._:-]{1,128})\]\]"
)

CONTENT_MESSAGE_TYPES = {
    "news_reaction",
    "research_ping",
    "memory_recall",
    "discovery",
    "content_share",
}


@dataclass
class DeliveryPayload:
    kind: str
    text: str = ""
    url: str = ""
    image_url: str = ""
    file_path: str = ""
    title: str = ""
    source: str = ""
    content_item_id: str = ""
    generated_by: str = "hermes"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "text": self.text,
            "url": self.url,
            "image_url": self.image_url,
            "file_path": self.file_path,
            "title": self.title,
            "source": self.source,
            "content_item_id": self.content_item_id,
            "generated_by": self.generated_by,
        }


@dataclass
class DeliveryOutcome:
    success: bool
    kind: str
    mode: str
    content_delivered: bool
    fallback_used: bool = False
    error: str | None = None
    result: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "kind": self.kind,
            "mode": self.mode,
            "content_delivered": self.content_delivered,
            "fallback_used": self.fallback_used,
            "error": self.error,
        }


@dataclass
class DeliveryPlan:
    text_messages: list[tuple[str, str, str]]
    rich_payload: DeliveryPayload | None
    selected_item: dict[str, Any] | None
    evidence_score: int
    max_units: int


def _safe_http_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith("//"):
        raw = "https:" + raw
    try:
        parsed = urlparse(raw)
    except Exception:
        return ""
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return raw


def _result_success(result: Any) -> bool:
    if result is None:
        return True
    if isinstance(result, bool):
        return result
    if isinstance(result, dict):
        if "success" in result:
            return bool(result.get("success"))
        if result.get("error"):
            return False
        return True
    success = getattr(result, "success", None)
    if success is not None:
        return bool(success)
    return True


def _result_error(result: Any) -> str | None:
    if result is None:
        return None
    if isinstance(result, dict):
        value = result.get("error")
        return str(value) if value else None
    value = getattr(result, "error", None)
    return str(value) if value else None


def _combined_message_text(
    messages: list[tuple[str, str, str]],
) -> str:
    return "\n".join(str(message[1]) for message in messages).lower()


def _item_evidence_score(
    item: dict[str, Any],
    messages: list[tuple[str, str, str]],
) -> int:
    combined = _combined_message_text(messages)
    url = _safe_http_url(
        item.get("url")
        or item.get("link")
        or item.get("href")
    ).lower()
    title = str(item.get("title") or "").strip().lower()
    summary = str(
        item.get("summary")
        or item.get("description")
        or ""
    ).strip().lower()
    source = str(item.get("source") or "").strip().lower()

    if url and url in combined:
        return 100
    if title and len(title) >= 5 and title in combined:
        return 90

    score = 0
    blob = f"{title} {summary}".strip()
    ascii_tokens = [
        token
        for token in re.findall(r"[a-z0-9+#.]{3,}", blob)
        if token not in {
            "with",
            "from",
            "that",
            "this",
            "the",
            "and",
            "for",
            "into",
            "using",
        }
    ]
    for token in set(ascii_tokens):
        if re.search(
            rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])",
            combined,
        ):
            score += 10

    chinese = "".join(
        re.findall(r"[\u4e00-\u9fff]", blob)
    )
    bigrams = {
        chinese[index:index + 2]
        for index in range(max(0, len(chinese) - 1))
    }
    matched = sum(
        1 for pair in bigrams if pair in combined
    )
    score += min(50, matched * 5)

    if source and source in combined:
        score += 10

    message_types = {
        str(message[0])
        for message in messages
    }
    if message_types & CONTENT_MESSAGE_TYPES:
        score += 10

    return score


class ContentDeliveryEngine:
    def __init__(
        self,
        *,
        allowed_file_roots: list[Path | str] | None = None,
        max_file_bytes: int | None = None,
    ) -> None:
        if allowed_file_roots is None:
            raw_roots = os.getenv(
                "HERMES_ALIVE_DELIVERY_FILE_ROOTS",
                "/opt/data/hermes_alive_shared",
            )
            allowed_file_roots = [
                value.strip()
                for value in raw_roots.split(",")
                if value.strip()
            ]
        self.allowed_file_roots = [
            Path(value).resolve()
            for value in allowed_file_roots
        ]
        self.max_file_bytes = int(
            max_file_bytes
            if max_file_bytes is not None
            else os.getenv(
                "HERMES_ALIVE_DELIVERY_MAX_FILE_BYTES",
                str(25 * 1024 * 1024),
            )
        )

    def plan(
        self,
        messages: list[tuple[str, str, str]],
        discovery_context: dict[str, Any] | None,
        policy_decision: dict[str, Any] | None,
        *,
        content_ref: str | None = None,
        content_generated_by: str | None = None,
    ) -> DeliveryPlan:
        cleaned = [
            (
                str(msg_type),
                str(content).strip(),
                str(generated_by or "hermes"),
            )
            for msg_type, content, generated_by in messages
            if str(content).strip()
        ]

        max_units = 3
        allow_content_share = True
        if isinstance(policy_decision, dict):
            try:
                max_units = int(
                    policy_decision.get(
                        "max_bubbles",
                        max_units,
                    )
                )
            except Exception:
                max_units = 3
            allow_content_share = bool(
                policy_decision.get(
                    "allow_content_share",
                    True,
                )
            )
        max_units = max(1, min(5, max_units))

        if not allow_content_share:
            return DeliveryPlan(
                text_messages=cleaned[:max_units],
                rich_payload=None,
                selected_item=None,
                evidence_score=0,
                max_units=max_units,
            )

        item: dict[str, Any] | None
        evidence_score: int
        if content_ref:
            item = self._item_by_ref(
                discovery_context,
                content_ref,
            )
            evidence_score = 1000 if item is not None else 0
        else:
            item, evidence_score = self._select_item(
                discovery_context,
                cleaned,
            )
        payload_generated_by = str(
            content_generated_by or ""
        ).strip()
        if not payload_generated_by:
            payload_generated_by = next(
                (
                    generated_by
                    for _msg_type, _content, generated_by
                    in cleaned
                    if generated_by != "hermes"
                ),
                "hermes",
            )

        rich_payload = (
            self._build_payload(
                item,
                cleaned,
                generated_by=payload_generated_by,
            )
            if item is not None and evidence_score >= 20
            else None
        )

        if rich_payload is None:
            return DeliveryPlan(
                text_messages=cleaned[:max_units],
                rich_payload=None,
                selected_item=item,
                evidence_score=evidence_score,
                max_units=max_units,
            )

        text_limit = max(0, max_units - 1)
        return DeliveryPlan(
            text_messages=cleaned[:text_limit],
            rich_payload=rich_payload,
            selected_item=item,
            evidence_score=evidence_score,
            max_units=max_units,
        )

    def _item_by_ref(
        self,
        discovery_context: dict[str, Any] | None,
        content_ref: str,
    ) -> dict[str, Any] | None:
        # RICH_CONTENT_REFERENCE_V1
        if not isinstance(discovery_context, dict):
            return None
        external = discovery_context.get("external")
        if not isinstance(external, list):
            return None

        target = str(content_ref or "").strip()
        if not target:
            return None

        for value in external:
            if not isinstance(value, dict):
                continue
            item_id = str(value.get("id") or "").strip()
            if item_id and item_id == target:
                return value
        return None

    def _select_item(
        self,
        discovery_context: dict[str, Any] | None,
        messages: list[tuple[str, str, str]],
    ) -> tuple[dict[str, Any] | None, int]:
        if not isinstance(discovery_context, dict):
            return None, 0

        external = discovery_context.get("external")
        if not isinstance(external, list):
            return None, 0

        candidates: list[tuple[int, dict[str, Any]]] = []
        for value in external:
            if isinstance(value, dict):
                score = _item_evidence_score(
                    value,
                    messages,
                )
                candidates.append((score, value))

        if not candidates:
            return None, 0

        score, item = max(
            candidates,
            key=lambda value: value[0],
        )
        return item, score

    def _build_payload(
        self,
        item: dict[str, Any],
        messages: list[tuple[str, str, str]],
        *,
        generated_by: str,
    ) -> DeliveryPayload | None:
        title = str(item.get("title") or "").strip()
        source = str(item.get("source") or "").strip()
        item_id = str(item.get("id") or "").strip()
        url = _safe_http_url(
            item.get("url")
            or item.get("link")
            or item.get("href")
        )
        image_url = _safe_http_url(
            item.get("image_url")
            or item.get("thumbnail_url")
            or item.get("thumbnail")
            or item.get("image")
        )
        file_path = str(
            item.get("file_path")
            or item.get("local_path")
            or ""
        ).strip()

        caption_parts = [
            part
            for part in (title, url)
            if part
        ]
        caption = "\n".join(caption_parts)

        if file_path:
            return DeliveryPayload(
                kind="file",
                text=caption,
                url=url,
                file_path=file_path,
                title=title,
                source=source,
                content_item_id=item_id,
                generated_by=generated_by,
            )

        if image_url:
            return DeliveryPayload(
                kind="image",
                text=caption,
                url=url,
                image_url=image_url,
                title=title,
                source=source,
                content_item_id=item_id,
                generated_by=generated_by,
            )

        if url and url not in _combined_message_text(messages):
            return DeliveryPayload(
                kind="link",
                text=caption or url,
                url=url,
                title=title,
                source=source,
                content_item_id=item_id,
                generated_by=generated_by,
            )

        return None

    def _safe_file_path(
        self,
        raw_path: str,
    ) -> Path | None:
        if not raw_path:
            return None
        try:
            path = Path(
                raw_path.replace("file://", "")
            ).expanduser().resolve()
        except Exception:
            return None

        if not path.is_file():
            return None

        try:
            size = path.stat().st_size
        except Exception:
            return None
        if size < 0 or size > self.max_file_bytes:
            return None

        for root in self.allowed_file_roots:
            try:
                path.relative_to(root)
                return path
            except ValueError:
                continue
        return None

    async def send_text(
        self,
        adapter: Any,
        chat_id: str,
        content: str,
        *,
        metadata: dict[str, Any],
    ) -> DeliveryOutcome:
        try:
            result = await adapter.send(
                chat_id,
                content,
                metadata=metadata,
            )
        except Exception as exc:
            return DeliveryOutcome(
                success=False,
                kind="text",
                mode="text",
                content_delivered=False,
                error=f"{type(exc).__name__}: {exc}",
            )

        success = _result_success(result)
        return DeliveryOutcome(
            success=success,
            kind="text",
            mode="text",
            content_delivered=success,
            error=None if success else _result_error(result),
            result=result,
        )

    async def send_rich(
        self,
        adapter: Any,
        chat_id: str,
        payload: DeliveryPayload,
        *,
        metadata: dict[str, Any],
    ) -> DeliveryOutcome:
        if payload.kind == "image":
            return await self._send_image(
                adapter,
                chat_id,
                payload,
                metadata=metadata,
            )
        if payload.kind == "file":
            return await self._send_file(
                adapter,
                chat_id,
                payload,
                metadata=metadata,
            )
        if payload.kind == "link":
            return await self._send_link(
                adapter,
                chat_id,
                payload,
                metadata=metadata,
            )
        return DeliveryOutcome(
            success=False,
            kind=payload.kind,
            mode="unsupported",
            content_delivered=False,
            error="unsupported_payload_kind",
        )

    async def _send_image(
        self,
        adapter: Any,
        chat_id: str,
        payload: DeliveryPayload,
        *,
        metadata: dict[str, Any],
    ) -> DeliveryOutcome:
        method = getattr(adapter, "send_image", None)
        if callable(method):
            try:
                result = await method(
                    chat_id=chat_id,
                    image_url=payload.image_url,
                    caption=payload.text,
                    metadata=metadata,
                )
                if _result_success(result):
                    return DeliveryOutcome(
                        success=True,
                        kind="image",
                        mode="native_image",
                        content_delivered=True,
                        result=result,
                    )
            except Exception:
                pass

        fallback_text = "\n".join(
            value
            for value in (
                payload.text,
                payload.image_url,
            )
            if value
        )
        return await self._send_text_fallback(
            adapter,
            chat_id,
            fallback_text,
            metadata=metadata,
            kind="image",
            mode="image_url_fallback",
            content_delivered=bool(payload.image_url),
        )

    async def _send_file(
        self,
        adapter: Any,
        chat_id: str,
        payload: DeliveryPayload,
        *,
        metadata: dict[str, Any],
    ) -> DeliveryOutcome:
        safe_path = self._safe_file_path(
            payload.file_path
        )
        method = getattr(
            adapter,
            "send_document",
            None,
        )
        if safe_path is not None and callable(method):
            try:
                result = await method(
                    chat_id=chat_id,
                    file_path=str(safe_path),
                    caption=payload.text,
                    metadata=metadata,
                )
                if _result_success(result):
                    return DeliveryOutcome(
                        success=True,
                        kind="file",
                        mode="native_file",
                        content_delivered=True,
                        result=result,
                    )
            except Exception:
                pass

        if payload.url:
            return await self._send_text_fallback(
                adapter,
                chat_id,
                payload.text or payload.url,
                metadata=metadata,
                kind="file",
                mode="file_link_fallback",
                content_delivered=True,
            )

        return DeliveryOutcome(
            success=False,
            kind="file",
            mode="file_unavailable",
            content_delivered=False,
            error="unsafe_missing_or_unsupported_file",
        )

    async def _send_link(
        self,
        adapter: Any,
        chat_id: str,
        payload: DeliveryPayload,
        *,
        metadata: dict[str, Any],
    ) -> DeliveryOutcome:
        method = getattr(
            adapter,
            "send_link_card",
            None,
        )
        if callable(method):
            try:
                result = await method(
                    chat_id=chat_id,
                    title=payload.title,
                    url=payload.url,
                    description=payload.text,
                    metadata=metadata,
                )
                if _result_success(result):
                    return DeliveryOutcome(
                        success=True,
                        kind="link",
                        mode="native_link_card",
                        content_delivered=True,
                        result=result,
                    )
            except Exception:
                pass

        return await self._send_text_fallback(
            adapter,
            chat_id,
            payload.text or payload.url,
            metadata=metadata,
            kind="link",
            mode="text_link_fallback",
            content_delivered=bool(payload.url),
        )

    async def _send_text_fallback(
        self,
        adapter: Any,
        chat_id: str,
        text: str,
        *,
        metadata: dict[str, Any],
        kind: str,
        mode: str,
        content_delivered: bool,
    ) -> DeliveryOutcome:
        if not text.strip():
            return DeliveryOutcome(
                success=False,
                kind=kind,
                mode=mode,
                content_delivered=False,
                fallback_used=True,
                error="empty_fallback_text",
            )

        try:
            result = await adapter.send(
                chat_id,
                text,
                metadata=metadata,
            )
        except Exception as exc:
            return DeliveryOutcome(
                success=False,
                kind=kind,
                mode=mode,
                content_delivered=False,
                fallback_used=True,
                error=f"{type(exc).__name__}: {exc}",
            )

        success = _result_success(result)
        return DeliveryOutcome(
            success=success,
            kind=kind,
            mode=mode,
            content_delivered=(
                success and content_delivered
            ),
            fallback_used=True,
            error=None if success else _result_error(result),
            result=result,
        )
