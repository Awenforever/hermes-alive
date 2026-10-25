from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FakeResult:
    success: bool = True
    error: str | None = None


class FakeAdapter:
    def __init__(
        self,
        *,
        fail_text_every: int = 0,
        fail_image_every: int = 0,
        fail_document_every: int = 0,
        raise_text_every: int = 0,
    ) -> None:
        self.fail_text_every = fail_text_every
        self.fail_image_every = fail_image_every
        self.fail_document_every = fail_document_every
        self.raise_text_every = raise_text_every
        self.calls: list[dict[str, Any]] = []
        self._counts = {"text": 0, "image": 0, "document": 0}

    def _next(self, kind: str) -> int:
        self._counts[kind] += 1
        return self._counts[kind]

    async def send(self, chat_id, content, reply_to=None, metadata=None):
        index = self._next("text")
        self.calls.append({
            "kind": "text",
            "index": index,
            "chat_id": chat_id,
            "content": content,
            "metadata": dict(metadata or {}),
        })
        if self.raise_text_every and index % self.raise_text_every == 0:
            raise RuntimeError("injected_text_exception")
        if self.fail_text_every and index % self.fail_text_every == 0:
            return FakeResult(False, "injected_text_failure")
        return FakeResult(True)

    async def send_image(self, chat_id, image_url, caption, reply_to=None, metadata=None):
        index = self._next("image")
        self.calls.append({
            "kind": "image",
            "index": index,
            "chat_id": chat_id,
            "image_url": image_url,
            "caption": caption,
            "metadata": dict(metadata or {}),
        })
        if self.fail_image_every and index % self.fail_image_every == 0:
            return FakeResult(False, "injected_image_failure")
        return FakeResult(True)

    async def send_document(self, chat_id, file_path, caption=None, file_name=None, reply_to=None, metadata=None, **kwargs):
        index = self._next("document")
        self.calls.append({
            "kind": "document",
            "index": index,
            "chat_id": chat_id,
            "file_path": file_path,
            "caption": caption,
            "metadata": dict(metadata or {}),
        })
        if self.fail_document_every and index % self.fail_document_every == 0:
            return FakeResult(False, "injected_document_failure")
        return FakeResult(True)
