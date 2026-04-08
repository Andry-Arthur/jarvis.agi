"""Abstract LLM interface shared by all providers."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


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


class BaseLLM(ABC):
    """Abstract base for all LLM provider implementations."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        """Send messages and return a response, optionally calling tools."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True when the provider is configured and reachable."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...
