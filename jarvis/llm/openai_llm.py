"""OpenAI LLM provider with true token streaming."""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from jarvis.llm.base import BaseLLM, LLMResponse, StreamChunk, ToolCall

logger = logging.getLogger(__name__)


class OpenAILLM(BaseLLM):
    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        from openai import AsyncOpenAI

        self._api_key = api_key
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _build_messages(self, messages: list[dict], system: str | None) -> list[dict]:
        all_messages: list[dict] = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)
        return all_messages

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        kwargs: dict = {
            "model": self.model,
            "messages": self._build_messages(messages, system),
        }
        if tools:
            kwargs["tools"] = tools

        response = await self.client.chat.completions.create(**kwargs)
        msg = response.choices[0].message

        tool_calls: list[ToolCall] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(
                    ToolCall(id=tc.id, name=tc.function.name, arguments=args)
                )

        return LLMResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            model=response.model,
        )

    async def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """True token-by-token streaming via OpenAI's streaming API."""
        kwargs: dict = {
            "model": self.model,
            "messages": self._build_messages(messages, system),
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools

        # Accumulate tool call deltas
        tc_accum: dict[int, dict] = {}  # index → partial tool call

        async with await self.client.chat.completions.create(**kwargs) as stream:
            async for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                if choice is None:
                    continue

                delta = choice.delta

                # Stream text tokens
                if delta.content:
                    yield StreamChunk(delta=delta.content, model=chunk.model or self.model)

                # Accumulate tool call fragments
                if delta.tool_calls:
                    for tc_delta in delta.tool_calls:
                        idx = tc_delta.index
                        if idx not in tc_accum:
                            tc_accum[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc_delta.id:
                            tc_accum[idx]["id"] = tc_delta.id
                        if tc_delta.function:
                            if tc_delta.function.name:
                                tc_accum[idx]["name"] += tc_delta.function.name
                            if tc_delta.function.arguments:
                                tc_accum[idx]["arguments"] += tc_delta.function.arguments

                if choice.finish_reason in ("stop", "tool_calls", "length"):
                    break

        # Emit accumulated tool calls at the end
        tool_calls: list[ToolCall] = []
        for tc_data in tc_accum.values():
            try:
                args = json.loads(tc_data["arguments"])
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(
                ToolCall(id=tc_data["id"], name=tc_data["name"], arguments=args)
            )

        yield StreamChunk(tool_calls=tool_calls, done=True, model=self.model)
