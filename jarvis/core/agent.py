"""JARVIS Agent — the main LLM tool-calling loop."""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from jarvis.core.tools import ToolRegistry
from jarvis.llm.router import LLMRouter

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are JARVIS, a highly capable AI personal assistant. You have access to the following tools:

- **Gmail**: Read emails, search your inbox, send emails, archive messages
- **Discord**: Send messages to channels, read channel history
- **YouTube**: Search for videos, get video transcripts and summaries
- **Instagram**: Read and send Instagram DMs

Guidelines:
- Be concise and conversational — you're speaking to the user directly.
- When using tools, briefly announce what you're doing before calling them.
- Combine multiple tool results when answering complex questions.
- If a tool fails, explain why and suggest alternatives.
- Remember the user's preferences and context from the conversation.
- Always respond in a helpful, proactive tone.
"""


class AgentEvent:
    """A structured event emitted during agent execution for streaming."""

    def __init__(self, kind: str, data: dict) -> None:
        self.kind = kind  # "thinking" | "tool_call" | "tool_result" | "chunk" | "done" | "error"
        self.data = data

    def to_dict(self) -> dict:
        return {"type": self.kind, **self.data}


class Agent:
    def __init__(
        self,
        llm_router: LLMRouter,
        tool_registry: ToolRegistry,
        memory: "Memory | None" = None,  # type: ignore[name-defined]
        max_iterations: int = 10,
    ) -> None:
        self.llm = llm_router
        self.tools = tool_registry
        self.memory = memory
        self.max_iterations = max_iterations

    # ------------------------------------------------------------------
    # Simple (non-streaming) run
    # ------------------------------------------------------------------

    async def run(
        self,
        user_message: str,
        history: list[dict] | None = None,
        provider: str | None = None,
    ) -> str:
        messages: list[dict] = list(history or [])
        messages.append({"role": "user", "content": user_message})

        system = SYSTEM_PROMPT
        if self.memory:
            context = await self.memory.get_relevant_context(user_message)
            if context:
                system += f"\n\nContext from memory:\n{context}"

        available_tools = self.tools.get_all_schemas()

        for iteration in range(self.max_iterations):
            response = await self.llm.chat(
                messages,
                tools=available_tools if available_tools else None,
                system=system,
                provider=provider,
            )

            if not response.tool_calls:
                if self.memory:
                    await self.memory.add_exchange(user_message, response.content)
                return response.content

            # Append assistant turn with tool calls
            messages.append(
                {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [tc.to_openai_dict() for tc in response.tool_calls],
                }
            )

            # Execute each tool and append results
            for tc in response.tool_calls:
                logger.info("Calling tool '%s' with args: %s", tc.name, tc.arguments)
                result = await self.tools.execute(tc.name, tc.arguments)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )

        return "I've reached the maximum number of steps. Please try rephrasing your request."

    # ------------------------------------------------------------------
    # Streaming run (yields AgentEvent objects)
    # ------------------------------------------------------------------

    async def stream(
        self,
        user_message: str,
        history: list[dict] | None = None,
        provider: str | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        messages: list[dict] = list(history or [])
        messages.append({"role": "user", "content": user_message})

        system = SYSTEM_PROMPT
        if self.memory:
            context = await self.memory.get_relevant_context(user_message)
            if context:
                system += f"\n\nContext from memory:\n{context}"

        available_tools = self.tools.get_all_schemas()

        for iteration in range(self.max_iterations):
            response = await self.llm.chat(
                messages,
                tools=available_tools if available_tools else None,
                system=system,
                provider=provider,
            )

            if not response.tool_calls:
                if self.memory:
                    await self.memory.add_exchange(user_message, response.content)
                yield AgentEvent("done", {"content": response.content, "model": response.model})
                return

            # Emit tool call events
            messages.append(
                {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [tc.to_openai_dict() for tc in response.tool_calls],
                }
            )

            for tc in response.tool_calls:
                yield AgentEvent("tool_call", {"name": tc.name, "args": tc.arguments})
                result = await self.tools.execute(tc.name, tc.arguments)
                yield AgentEvent("tool_result", {"name": tc.name, "result": result})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )

        yield AgentEvent(
            "error",
            {"content": "Maximum steps reached. Please try a simpler request."},
        )
