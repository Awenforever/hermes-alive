from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
TEST_SHARED = Path(
    tempfile.mkdtemp(prefix="ha-rich-attribution-")
)
os.environ["HERMES_ALIVE_SHARED_DIR"] = str(TEST_SHARED)

HOOKS = ROOT / "hooks"
sys.path.insert(0, str(HOOKS))

from content_delivery import ContentDeliveryEngine, DeliveryOutcome, DeliveryPayload
from proactive_watcher import ProactivePlatformWatcher
from llm_message_composer import LLMMessageComposer


def context() -> dict:
    return {
        "external": [
            {
                "id": "paper-1",
                "title": "Synthetic research update",
                "url": "https://example.invalid/paper-1",
                "image_url": (
                    "https://example.invalid/paper-1.jpg"
                ),
                "source": "synthetic",
            }
        ]
    }


def policy() -> dict:
    return {
        "allow_content_share": True,
        "max_bubbles": 2,
    }


def test_explicit_model_content_ref() -> None:
    engine = ContentDeliveryEngine()
    plan = engine.plan(
        [],
        context(),
        policy(),
        content_ref="paper-1",
        content_generated_by="fake-provider/fake-model",
    )
    assert plan.rich_payload is not None
    assert (
        plan.rich_payload.generated_by
        == "fake-provider/fake-model"
    )


def test_visible_model_inheritance() -> None:
    engine = ContentDeliveryEngine()
    plan = engine.plan(
        [
            (
                "research_ping",
                "Synthetic research update",
                "fake-provider/fake-model",
            )
        ],
        context(),
        policy(),
        content_ref="paper-1",
    )
    assert plan.rich_payload is not None
    assert (
        plan.rich_payload.generated_by
        == "fake-provider/fake-model"
    )


def test_explicit_system_provenance() -> None:
    engine = ContentDeliveryEngine()
    plan = engine.plan(
        [],
        context(),
        policy(),
        content_ref="paper-1",
        content_generated_by="hermes",
    )
    assert plan.rich_payload is not None
    assert plan.rich_payload.generated_by == "hermes"


def test_default_system_without_model() -> None:
    engine = ContentDeliveryEngine()
    plan = engine.plan(
        [],
        context(),
        policy(),
        content_ref="paper-1",
    )
    assert plan.rich_payload is not None
    assert plan.rich_payload.generated_by == "hermes"


def test_watcher_reference_provenance() -> None:
    watcher = ProactivePlatformWatcher(
        {},
        SimpleNamespace(),
    )
    messages = [
        (
            "__content_ref__",
            "paper-1",
            "fake-provider/fake-model",
        )
    ]
    assert (
        watcher._content_reference_generated_by(messages)
        == "fake-provider/fake-model"
    )
    visible, content_ref = (
        watcher._extract_content_reference(messages)
    )
    assert visible == []
    assert content_ref == "paper-1"


def test_watcher_system_reference_provenance() -> None:
    watcher = ProactivePlatformWatcher(
        {},
        SimpleNamespace(),
    )
    assert (
        watcher._content_reference_generated_by(
            [
                (
                    "__content_ref__",
                    "paper-1",
                    "hermes",
                )
            ]
        )
        == "hermes"
    )


def test_watcher_metadata_model_footer_contract() -> None:
    watcher = ProactivePlatformWatcher(
        {},
        SimpleNamespace(),
    )
    metadata = watcher._metadata(
        "fake-provider/fake-model"
    )
    assert metadata["is_system"] is False
    assert (
        metadata["resolved_model"]
        == "fake-provider/fake-model"
    )
    assert (
        metadata["routed_model"]
        == "fake-provider/fake-model"
    )


def test_watcher_metadata_system_contract() -> None:
    watcher = ProactivePlatformWatcher(
        {},
        SimpleNamespace(),
    )
    metadata = watcher._metadata("hermes")
    assert metadata["is_system"] is True
    assert metadata["resolved_model"] == "hermes"


def test_rich_logical_content_prefers_payload_text() -> None:
    watcher = ProactivePlatformWatcher(
        {},
        SimpleNamespace(),
    )
    payload = DeliveryPayload(
        kind="link",
        text=(
            "Synthetic title\n"
            "https://example.invalid/paper-1"
        ),
        title="Synthetic title",
        url="https://example.invalid/paper-1",
        content_item_id="paper-1",
        generated_by="fake-provider/fake-model",
    )
    assert (
        watcher._rich_delivery_logical_content(payload)
        == payload.text
    )


def test_rich_only_records_one_logical_sent_event() -> None:
    import proactive_watcher as watcher_module

    log_path = TEST_SHARED / "proactive_log.jsonl"
    log_path.unlink(missing_ok=True)
    watcher_module.PROACTIVE_LOG = log_path

    watcher = ProactivePlatformWatcher(
        {},
        SimpleNamespace(),
    )
    payload = DeliveryPayload(
        kind="link",
        text=(
            "Synthetic title\n"
            "https://example.invalid/paper-1"
        ),
        title="Synthetic title",
        url="https://example.invalid/paper-1",
        content_item_id="paper-1",
        generated_by="fake-provider/fake-model",
    )
    outcome = DeliveryOutcome(
        success=True,
        kind="link",
        mode="text_fallback",
        content_delivered=True,
        fallback_used=True,
    )

    watcher._record_rich_delivery_sent(
        "tick-rich-1",
        payload,
        outcome,
    )

    records = [
        json.loads(line)
        for line in log_path.read_text(
            encoding="utf-8",
        ).splitlines()
        if line.strip()
    ]
    sent = [
        record
        for record in records
        if record.get("decision") == "sent"
    ]
    assert len(sent) == 1
    record = sent[0]
    assert record["reason"] == "rich_proactive"
    assert record["msg_type"] == "content_share"
    assert record["generated_by"] == (
        "fake-provider/fake-model"
    )
    assert record["logical_delivery"] is True
    assert record["rich_kind"] == "link"
    assert record["content_item_id"] == "paper-1"


def _fake_response(
    content: str,
    model: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        model=model,
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=content,
                )
            )
        ],
    )


def _isolate_composer_prompt(
    composer: LLMMessageComposer,
) -> None:
    # This test targets response-model attribution only.  Avoid coupling it
    # to VoiceGenome fields, context files, weather, or prompt formatting.
    composer._system_prompt = lambda _voice: (
        "synthetic attribution system prompt"
    )

    async def fake_user_prompt(
        _voice,
        _context,
        _discovery_context=None,
    ):
        return "synthetic attribution user prompt"

    composer._user_prompt = fake_user_prompt


def test_composer_captures_primary_response_model() -> None:
    import agent.auxiliary_client as auxiliary_client

    original = auxiliary_client.async_call_llm

    async def fake_call(**_kwargs):
        return _fake_response(
            "真实 Provider 模型归属测试",
            "provider/actual-primary-model",
        )

    auxiliary_client.async_call_llm = fake_call
    try:
        composer = LLMMessageComposer()
        _isolate_composer_prompt(composer)
        value = asyncio.run(
            composer._generate_candidate(
                SimpleNamespace(),
                {},
                None,
            )
        )
        assert value == "真实 Provider 模型归属测试"
        assert (
            composer.last_resolved_model
            == "provider/actual-primary-model"
        )
    finally:
        auxiliary_client.async_call_llm = original


def test_composer_captures_fallback_response_model() -> None:
    import agent.auxiliary_client as auxiliary_client

    original = auxiliary_client.async_call_llm
    old_fallback = os.environ.get(
        "HERMES_PROACTIVE_LLM_FALLBACK_MODEL"
    )
    calls = {"count": 0}

    async def fake_call(**_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("injected primary failure")
        return _fake_response(
            "真实 fallback 模型归属测试",
            "provider/actual-fallback-model",
        )

    auxiliary_client.async_call_llm = fake_call
    os.environ[
        "HERMES_PROACTIVE_LLM_FALLBACK_MODEL"
    ] = "configured-fallback-alias"
    try:
        composer = LLMMessageComposer()
        _isolate_composer_prompt(composer)
        value = asyncio.run(
            composer._generate_candidate(
                SimpleNamespace(),
                {},
                None,
            )
        )
        assert value == "真实 fallback 模型归属测试"
        assert calls["count"] == 2
        assert (
            composer.last_resolved_model
            == "provider/actual-fallback-model"
        )
    finally:
        auxiliary_client.async_call_llm = original
        if old_fallback is None:
            os.environ.pop(
                "HERMES_PROACTIVE_LLM_FALLBACK_MODEL",
                None,
            )
        else:
            os.environ[
                "HERMES_PROACTIVE_LLM_FALLBACK_MODEL"
            ] = old_fallback


def test_watcher_prefers_actual_provider_model() -> None:
    class FakeComposer:
        last_resolved_model = (
            "provider/actual-runtime-model"
        )

        async def compose(
            self,
            _voice,
            context,
            discovery_context=None,
        ):
            del context, discovery_context
            return [
                (
                    "self_talk",
                    "真实模型归属",
                )
            ]

    watcher = ProactivePlatformWatcher(
        {},
        SimpleNamespace(),
    )
    watcher._llm_message_composer = FakeComposer()
    old_enabled = os.environ.get(
        "HERMES_PROACTIVE_LLM_ENABLED"
    )
    old_model = os.environ.get(
        "HERMES_PROACTIVE_LLM_MODEL"
    )
    os.environ[
        "HERMES_PROACTIVE_LLM_ENABLED"
    ] = "true"
    os.environ[
        "HERMES_PROACTIVE_LLM_MODEL"
    ] = "configured-static-alias"
    try:
        messages = asyncio.run(
            watcher._compose_message(
                SimpleNamespace(),
                None,
                policy_decision=None,
            )
        )
        assert messages == [
            (
                "self_talk",
                "真实模型归属",
                "provider/actual-runtime-model",
            )
        ]
    finally:
        if old_enabled is None:
            os.environ.pop(
                "HERMES_PROACTIVE_LLM_ENABLED",
                None,
            )
        else:
            os.environ[
                "HERMES_PROACTIVE_LLM_ENABLED"
            ] = old_enabled
        if old_model is None:
            os.environ.pop(
                "HERMES_PROACTIVE_LLM_MODEL",
                None,
            )
        else:
            os.environ[
                "HERMES_PROACTIVE_LLM_MODEL"
            ] = old_model


def test_watcher_falls_back_when_response_model_empty() -> None:
    class FakeComposer:
        last_resolved_model = ""

        async def compose(
            self,
            _voice,
            context,
            discovery_context=None,
        ):
            del context, discovery_context
            return [
                (
                    "self_talk",
                    "配置模型回退",
                )
            ]

    watcher = ProactivePlatformWatcher(
        {},
        SimpleNamespace(),
    )
    watcher._llm_message_composer = FakeComposer()
    old_enabled = os.environ.get(
        "HERMES_PROACTIVE_LLM_ENABLED"
    )
    old_model = os.environ.get(
        "HERMES_PROACTIVE_LLM_MODEL"
    )
    os.environ[
        "HERMES_PROACTIVE_LLM_ENABLED"
    ] = "true"
    os.environ[
        "HERMES_PROACTIVE_LLM_MODEL"
    ] = "configured-static-alias"
    try:
        messages = asyncio.run(
            watcher._compose_message(
                SimpleNamespace(),
                None,
                policy_decision=None,
            )
        )
        assert messages == [
            (
                "self_talk",
                "配置模型回退",
                "configured-static-alias",
            )
        ]
    finally:
        if old_enabled is None:
            os.environ.pop(
                "HERMES_PROACTIVE_LLM_ENABLED",
                None,
            )
        else:
            os.environ[
                "HERMES_PROACTIVE_LLM_ENABLED"
            ] = old_enabled
        if old_model is None:
            os.environ.pop(
                "HERMES_PROACTIVE_LLM_MODEL",
                None,
            )
        else:
            os.environ[
                "HERMES_PROACTIVE_LLM_MODEL"
            ] = old_model


TESTS = [
    test_explicit_model_content_ref,
    test_visible_model_inheritance,
    test_explicit_system_provenance,
    test_default_system_without_model,
    test_watcher_reference_provenance,
    test_watcher_system_reference_provenance,
    test_watcher_metadata_model_footer_contract,
    test_watcher_metadata_system_contract,
    test_rich_logical_content_prefers_payload_text,
    test_rich_only_records_one_logical_sent_event,
    test_composer_captures_primary_response_model,
    test_composer_captures_fallback_response_model,
    test_watcher_prefers_actual_provider_model,
    test_watcher_falls_back_when_response_model_empty,
]


def main() -> int:
    passed = 0
    for test in TESTS:
        test()
        passed += 1
        print(f"PASS {test.__name__}")
    print(
        "HERMES_ALIVE_RICH_CONTENT_MODEL_ATTRIBUTION_RESULT="
        f"PASS tests={passed}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
