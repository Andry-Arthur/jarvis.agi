"""Tool base class and registry for LLM function-calling."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class Tool(ABC):
    """Base class for all JARVIS tools exposed to the LLM."""

    # Subclasses must define these
    name: str
    description: str
    parameters: dict  # JSON Schema object

    @abstractmethod
    async def run(self, **kwargs: Any) -> str:
        """Execute the tool and return a string result."""
        ...

    def to_openai_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Holds all registered tools and dispatches calls from the agent."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> "ToolRegistry":
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s", tool.name)
        return self

    def register_many(self, tools: list[Tool]) -> "ToolRegistry":
        for tool in tools:
            self.register(tool)
        return self

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def get_all_schemas(self) -> list[dict]:
        return [t.to_openai_schema() for t in self._tools.values()]

    async def execute(self, name: str, arguments: dict) -> str:
        tool = self._tools.get(name)
        if tool is None:
            return f"Error: tool '{name}' not found."
        try:
            result = await tool.run(**arguments)
            return str(result)
        except Exception as exc:
            logger.exception("Tool '%s' raised an error", name)
            return f"Tool error: {exc}"

    @property
    def names(self) -> list[str]:
        return list(self._tools)
