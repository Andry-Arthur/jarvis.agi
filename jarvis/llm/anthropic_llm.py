"""Anthropic Claude LLM provider with true token streaming."""

from __future__ import annotations

import json
import logging
import uuid
from typing import AsyncGenerator

from jarvis.llm.base import BaseLLM, LLMResponse, StreamChunk, ToolCall

logger = logging.getLogger(__name__)


class AnthropicLLM(BaseLLM):
    def __init__(self, api_key: str, model: str = "claude-opus-4-5") -> None:
        from anthropic import AsyncAnthropic

        self._api_key = api_key
        self.model = model
        self.client = AsyncAnthropic(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _to_anthropic_messages(self, messages: list[dict]) -> list[dict]:
        converted: list[dict] = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg["role"]

            if role == "user":
                converted.append({"role": "user", "content": msg["content"]})

            elif role == "assistant":
                if msg.get("tool_calls"):
                    content: list[dict] = []
                    if msg.get("content"):
                        content.append({"type": "text", "text": msg["content"]})
                    for tc in msg["tool_calls"]:
                        content.append(
                            {
                                "type": "tool_use",
                                "id": tc["id"],
                                "name": tc["function"]["name"],
                                "input": json.loads(tc["function"]["arguments"]),
                            }
                        )
                    converted.append({"role": "assistant", "content": content})
                else:
                    converted.append(
                        {"role": "assistant", "content": msg.get("content", "")}
                    )

            elif role == "tool":
                tool_results: list[dict] = []
                while i < len(messages) and messages[i]["role"] == "tool":
                    tm = messages[i]
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tm["tool_call_id"],
                            "content": tm["content"],
                        }
                    )
                    i += 1
                converted.append({"role": "user", "content": tool_results})
                continue

            i += 1
        return converted

    def _to_anthropic_tools(self, tools: list[dict]) -> list[dict]:
        anthropic_tools = []
        for t in tools:
            fn = t.get("function", t)
            anthropic_tools.append(
                {
                    "name": fn["name"],
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
                }
            )
        return anthropic_tools

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": self._to_anthropic_messages(messages),
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._to_anthropic_tools(tools)

        response = await self.client.messages.create(**kwargs)

        content_text = ""
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=block.input or {})
                )

        return LLMResponse(content=content_text, tool_calls=tool_calls, model=response.model)

    async def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """True token-by-token streaming via Anthropic's streaming API."""
        kwargs: dict = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": self._to_anthropic_messages(messages),
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = self._to_anthropic_tools(tools)

        tool_calls: list[ToolCall] = []
        current_tool: dict | None = None

        async with self.client.messages.stream(**kwargs) as stream:
            async for event in stream:
                event_type = type(event).__name__

                if event_type == "RawContentBlockDeltaEvent":
                    delta = event.delta
                    if hasattr(delta, "text") and delta.text:
                        yield StreamChunk(delta=delta.text, model=self.model)
                    elif hasattr(delta, "partial_json") and delta.partial_json:
                        # Tool call argument accumulation
                        if current_tool is not None:
                            current_tool["arguments_raw"] = (
                                current_tool.get("arguments_raw", "") + delta.partial_json
                            )

                elif event_type == "RawContentBlockStartEvent":
                    block = event.content_block
                    if hasattr(block, "type") and block.type == "tool_use":
                        current_tool = {
                            "id": block.id,
                            "name": block.name,
                            "arguments_raw": "",
                        }

                elif event_type == "RawContentBlockStopEvent":
                    if current_tool is not None:
                        try:
                            args = json.loads(current_tool.get("arguments_raw", "{}"))
                        except json.JSONDecodeError:
                            args = {}
                        tool_calls.append(
                            ToolCall(
                                id=current_tool["id"],
                                name=current_tool["name"],
                                arguments=args,
                            )
                        )
                        current_tool = None

        yield StreamChunk(tool_calls=tool_calls, done=True, model=self.model)
