"""Anthropic Claude LLM provider.

Anthropic uses a different tool-calling format from OpenAI, so this module
converts between the unified internal format (OpenAI-style) and the Anthropic
wire format.
"""

from __future__ import annotations

import json
import logging
import uuid

from jarvis.llm.base import BaseLLM, LLMResponse, ToolCall

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

    # ------------------------------------------------------------------
    # Message format conversion
    # ------------------------------------------------------------------

    def _to_anthropic_messages(self, messages: list[dict]) -> list[dict]:
        """Convert OpenAI-style messages to Anthropic format."""
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
                # Collect consecutive tool results into a single user message
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
                continue  # i already advanced inside the while loop

            i += 1
        return converted

    def _to_anthropic_tools(self, tools: list[dict]) -> list[dict]:
        """Convert OpenAI function-calling schema to Anthropic tool schema."""
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

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        anthropic_messages = self._to_anthropic_messages(messages)

        kwargs: dict = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": anthropic_messages,
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
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input or {},
                    )
                )

        return LLMResponse(
            content=content_text,
            tool_calls=tool_calls,
            model=response.model,
        )
