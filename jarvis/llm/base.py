"""Abstract LLM interface shared by all providers."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict

    def to_openai_dict(self) -> dict:
        return {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.arguments),
            },
        }


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""


@dataclass
class StreamChunk:
    """A single streamed token or tool-call delta."""
    delta: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    done: bool = False
    model: str = ""


class BaseLLM(ABC):
    """Abstract base for all LLM provider implementations."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        """Send messages and return a complete response."""
        ...

    async def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream tokens as they are generated. Default: single chunk from chat()."""
        response = await self.chat(messages, tools=tools, system=system)
        yield StreamChunk(
            delta=response.content,
            tool_calls=response.tool_calls,
            done=True,
            model=response.model,
        )

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when the provider is configured and reachable."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...
