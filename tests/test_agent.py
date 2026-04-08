"""Unit tests for the Agent core loop."""

from __future__ import annotations

from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

from jarvis.core.agent import Agent
from jarvis.core.tools import Tool, ToolRegistry
from jarvis.llm.base import LLMResponse, StreamChunk, ToolCall
from jarvis.llm.router import LLMRouter


class GreetTool(Tool):
    name = "greet"
    description = "Greets someone by name."
    parameters = {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    }

    async def execute(self, name: str) -> str:
        return f"Hello, {name}!"


def make_router(responses: list[LLMResponse]) -> LLMRouter:
    router = MagicMock(spec=LLMRouter)
    router.available_providers = ["mock"]
    call_iter = iter(responses)
    router.chat = AsyncMock(side_effect=lambda *a, **kw: next(call_iter))

    async def _stream(*a, **kw):
        resp = await router.chat(*a, **kw)
        for tc in resp.tool_calls:
            yield StreamChunk(tool_calls=[tc], done=False)
        yield StreamChunk(delta=resp.content, done=True)

    router.stream_chat = _stream
    return router


@pytest.mark.asyncio
async def test_agent_simple_response():
    router = make_router([LLMResponse(content="Hello there!")])
    registry = ToolRegistry()
    agent = Agent(llm_router=router, tool_registry=registry)
    result = await agent.run("Hi")
    assert result == "Hello there!"


@pytest.mark.asyncio
async def test_agent_tool_call():
    tool_call = ToolCall(id="1", name="greet", arguments={"name": "Alice"})
    router = make_router(
        [
            LLMResponse(content="", tool_calls=[tool_call]),
            LLMResponse(content="I greeted Alice."),
        ]
    )
    registry = ToolRegistry()
    registry.register(GreetTool())
    agent = Agent(llm_router=router, tool_registry=registry)
    result = await agent.run("Say hello to Alice")
    assert "Alice" in result or result == "I greeted Alice."


@pytest.mark.asyncio
async def test_agent_stream_emits_chunks():
    router = make_router([LLMResponse(content="Streamed response")])
    registry = ToolRegistry()
    agent = Agent(llm_router=router, tool_registry=registry)

    events = []
    async for event in agent.stream("Tell me something"):
        events.append(event)

    kinds = [e.kind for e in events]
    assert "done" in kinds or "chunk" in kinds


@pytest.mark.asyncio
async def test_agent_max_iterations():
    """If every LLM response triggers a tool call, stop at max_iterations."""
    tool_call = ToolCall(id="1", name="greet", arguments={"name": "loop"})
    # Always returns a tool call — agent must stop
    router = MagicMock(spec=LLMRouter)
    router.available_providers = ["mock"]
    router.chat = AsyncMock(return_value=LLMResponse(content="", tool_calls=[tool_call]))

    async def _stream(*a, **kw):
        resp = await router.chat(*a, **kw)
        yield StreamChunk(tool_calls=resp.tool_calls, done=True)

    router.stream_chat = _stream

    registry = ToolRegistry()
    registry.register(GreetTool())
    agent = Agent(llm_router=router, tool_registry=registry, max_iterations=3)

    events = []
    async for event in agent.stream("loop forever"):
        events.append(event)

    kinds = [e.kind for e in events]
    assert "error" in kinds
