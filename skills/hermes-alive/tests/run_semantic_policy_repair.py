#!/usr/bin/env python3
"""A model bubble overflow is safely capped without losing provenance."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))

from llm_message_composer import LLMMessageComposer
from semantic_bubbles import parse_semantic_plan


payload = {
    "topic_mode": "new_discovery",
    "bubbles": [
        {"act": "discovery_intro", "text": "看到合肥刚发布了一项新的公共政策"},
        {"act": "fact", "text": "它会影响本地居民办理相关事项的流程"},
        {"act": "reaction", "text": "这次变化还挺值得留意"},
        {"act": "source_link", "text": "原始发布页面也在这里"},
    ],
    "content_ref": "news-123",
}
candidate, repaired = LLMMessageComposer._cap_candidate_to_policy(
    json.dumps(payload, ensure_ascii=False),
    {"mode": "novel_value", "max_bubbles": 3},
)
assert repaired is True
plan = parse_semantic_plan(
    candidate,
    default_msg_type="discovery_intro",
    policy_decision={"mode": "novel_value", "max_bubbles": 3},
    discovery_context={"external": [{"id": "news-123"}]},
)
assert len(plan.bubbles) == 3
assert plan.content_ref == "news-123"
assert plan.bubbles[0].text == payload["bubbles"][0]["text"]
assert plan.bubbles[2].text == payload["bubbles"][2]["text"]

print("HERMES_ALIVE_SEMANTIC_POLICY_REPAIR_RESULT=PASS")
