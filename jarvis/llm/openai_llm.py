"""OpenAI LLM provider."""

from __future__ import annotations

import json
import logging

from jarvis.llm.base import BaseLLM, LLMResponse, ToolCall

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

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        all_messages: list[dict] = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        kwargs: dict = {"model": self.model, "messages": all_messages}
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
