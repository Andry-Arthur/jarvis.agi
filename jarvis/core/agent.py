"""JARVIS Agent — the main LLM tool-calling loop with streaming and retry."""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from jarvis.core.tools import ToolRegistry
from jarvis.llm.router import LLMRouter

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are JARVIS, a highly capable AI personal assistant. You have access to many tools:

- **Gmail**: Read, search, send, and archive emails
- **Discord**: Send messages to channels, read channel history
- **YouTube**: Search for videos, get transcripts and summaries
- **Instagram**: Read and send Instagram DMs
- **Google Calendar**: List events, create events, find free slots
- **Google Drive**: Search, read, and create documents
- **WhatsApp**: Send and read WhatsApp messages
- **Telegram**: Send messages and files via Telegram
- **Spotify**: Play, pause, search tracks, manage playlists
- **Slack**: Send messages, read channels
- **Browser**: Navigate websites, fill forms, extract text
- **File System**: Read, write, and search files
- **Code Execution**: Run Python scripts and shell commands
- **Screen Vision**: Capture and read screen content
- **Computer Control**: Click, type, and automate desktop tasks
- **Knowledge Base**: Search your personal document library
- **Reminders**: Set and manage reminders and scheduled tasks

Guidelines:
- Be concise and conversational — you're speaking to the user directly.
- When using tools, briefly announce what you're doing before calling them.
- Combine multiple tool results when answering complex questions.
- If a tool fails, explain why and suggest alternatives.
- Remember the user's preferences and context from the conversation.
- Always respond in a helpful, proactive tone.
"""

_TOOL_MAX_RETRIES = 1  # retry each failed tool call once before reporting


class AgentEvent:
    """A structured event emitted during agent execution for streaming."""

    def __init__(self, kind: str, data: dict) -> None:
        self.kind = kind  # "thinking" | "tool_call" | "tool_result" | "chunk" | "done" | "error"
        self.data = data

    def to_dict(self) -> dict:
        return {"type": self.kind, **self.data}


async def _execute_with_retry(registry: ToolRegistry, name: str, args: dict) -> str:
    """Execute a tool, retrying once on failure."""
    last_error: Exception | None = None
    for attempt in range(_TOOL_MAX_RETRIES + 1):
        try:
            return await registry.execute(name, args)
        except Exception as exc:
            last_error = exc
            if attempt < _TOOL_MAX_RETRIES:
                logger.warning(
                    "Tool '%s' failed (attempt %d), retrying: %s", name, attempt + 1, exc
                )
    return f"[Tool '{name}' failed after {_TOOL_MAX_RETRIES + 1} attempts: {last_error}]"


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
        multimodal_suffix: str | None = None,
    ) -> str:
        messages: list[dict] = list(history or [])
        messages.append({"role": "user", "content": user_message})

        system = SYSTEM_PROMPT
        if multimodal_suffix:
            system += multimodal_suffix
        if self.memory:
            context = await self.memory.get_relevant_context(user_message)
            if context:
                system += f"\n\nContext from memory:\n{context}"

        available_tools = self.tools.get_all_schemas()

        for _iteration in range(self.max_iterations):
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

            messages.append(
                {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [tc.to_openai_dict() for tc in response.tool_calls],
                }
            )

            for tc in response.tool_calls:
                logger.info("Calling tool '%s' with args: %s", tc.name, tc.arguments)
                result = await _execute_with_retry(self.tools, tc.name, tc.arguments)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )

        return "I've reached the maximum number of steps. Please try rephrasing your request."

    # ------------------------------------------------------------------
    # Streaming run — yields AgentEvent objects with real token streaming
    # ------------------------------------------------------------------

    async def stream(
        self,
        user_message: str,
        history: list[dict] | None = None,
        provider: str | None = None,
        multimodal_suffix: str | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        messages: list[dict] = list(history or [])
        messages.append({"role": "user", "content": user_message})

        system = SYSTEM_PROMPT
        if multimodal_suffix:
            system += multimodal_suffix
        if self.memory:
            context = await self.memory.get_relevant_context(user_message)
            if context:
                system += f"\n\nContext from memory:\n{context}"

        available_tools = self.tools.get_all_schemas()

        for _iteration in range(self.max_iterations):
            accumulated_text = ""
            accumulated_tool_calls = []

            # True streaming: emit tokens as they arrive
            async for chunk in self.llm.stream_chat(
                messages,
                tools=available_tools if available_tools else None,
                system=system,
                provider=provider,
            ):
                if chunk.delta:
                    accumulated_text += chunk.delta
                    yield AgentEvent("chunk", {"delta": chunk.delta, "model": chunk.model})
                if chunk.tool_calls:
                    accumulated_tool_calls = chunk.tool_calls

            if not accumulated_tool_calls:
                if self.memory:
                    await self.memory.add_exchange(user_message, accumulated_text)
                yield AgentEvent(
                    "done",
                    {"content": accumulated_text, "model": ""},
                )
                return

            # Append assistant message with tool calls
            messages.append(
                {
                    "role": "assistant",
                    "content": accumulated_text,
                    "tool_calls": [tc.to_openai_dict() for tc in accumulated_tool_calls],
                }
            )

            for tc in accumulated_tool_calls:
                yield AgentEvent("tool_call", {"name": tc.name, "args": tc.arguments})
                result = await _execute_with_retry(self.tools, tc.name, tc.arguments)
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
