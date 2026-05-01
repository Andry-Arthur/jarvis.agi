"""Tests for multimodal event normalization, fusion, and throttling."""

from __future__ import annotations

import time

import pytest

from jarvis.multimodal.events import normalize_multimodal_event, normalize_multimodal_payload
from jarvis.multimodal.fusion import MultimodalFusionState
from jarvis.multimodal.throttle import TokenBucket


def test_normalize_gesture_event():
    raw = {"kind": "gesture", "label": "wave", "confidence": 1.5}
    out = normalize_multimodal_event(raw)
    assert out is not None
    assert out["kind"] == "gesture"
    assert out["label"] == "wave"
    assert out["confidence"] == 1.0


def test_normalize_batch():
    payload = {
        "events": [
            {"kind": "emotion", "label": "happy"},
            {"kind": "invalid_kind"},
        ]
    }
    evs = normalize_multimodal_payload(payload)
    assert len(evs) == 1
    assert evs[0]["label"] == "happy"


def test_fusion_suffix_and_prune(monkeypatch):
    monkeypatch.setenv("MULTIMODAL_FUSION_WINDOW_S", "2")
    monkeypatch.setenv("MULTIMODAL_MAX_CONTEXT_CHARS", "2000")
    fusion = MultimodalFusionState(window_s=2.0)
    t0 = time.time()
    fusion.ingest(
        {
            "kind": "gesture",
            "label": "attention_request",
            "confidence": 0.9,
            "ts": t0,
        }
    )
    suf = fusion.get_context_suffix(now=t0 + 0.5)
    assert "attention_request" in suf
    assert "Multimodal context" in suf

    fusion.ingest({"kind": "gesture", "label": "old", "ts": t0 - 100})
    fusion._prune(t0 + 0.5)
    assert len(fusion._events) >= 1


def test_token_bucket():
    b = TokenBucket(rate=10.0, capacity=2.0)
    assert b.consume()
    assert b.consume()
    assert not b.consume()


@pytest.mark.asyncio
async def test_agent_stream_multimodal_suffix(monkeypatch):
    """stream_chat receives system prompt augmented with multimodal suffix."""
    from unittest.mock import AsyncMock, MagicMock

    from jarvis.core.agent import Agent
    from jarvis.core.tools import ToolRegistry
    from jarvis.llm.base import LLMResponse, StreamChunk
    from jarvis.llm.router import LLMRouter

    kwargs_seen: dict = {}

    async def stream_chat(messages, tools=None, system=None, provider=None):
        kwargs_seen["system"] = system
        yield StreamChunk(delta="Hi", model="m")

    router = MagicMock(spec=LLMRouter)
    router.available_providers = ["mock"]
    router.stream_chat = stream_chat

    agent = Agent(llm_router=router, tool_registry=ToolRegistry())
    suffix = "\n\nMultimodal context test."
    async for _ in agent.stream("Hello", multimodal_suffix=suffix):
        pass

    assert kwargs_seen.get("system") is not None
    assert "Multimodal context test" in kwargs_seen["system"]
