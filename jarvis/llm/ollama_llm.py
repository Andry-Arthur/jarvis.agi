"""Ollama local LLM provider with streaming support.

Requires Ollama running at OLLAMA_BASE_URL (default http://localhost:11434).

Tool calling with small local models (llama3.1 8B, etc.) is unreliable and
slow on CPU — the model tends to invoke tools for every message, even simple
greetings.  Set OLLAMA_TOOLS_ENABLED=true in .env to opt in; by default tools
are disabled so you get fast, reliable conversational responses.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import AsyncGenerator

import httpx

from jarvis.llm.base import BaseLLM, LLMResponse, StreamChunk, ToolCall

logger = logging.getLogger(__name__)

_TOOLS_ENABLED = os.getenv("OLLAMA_TOOLS_ENABLED", "false").lower() == "true"


def _msg_content(msg) -> str:
    """Extract text content from an Ollama message object (dict or Pydantic)."""
    if msg is None:
        return ""
    if hasattr(msg, "get"):
        return msg.get("content", "") or ""
    return getattr(msg, "content", "") or ""


def _msg_tool_calls(msg) -> list:
    """Extract tool_calls list from an Ollama message object."""
    if msg is None:
        return []
    if hasattr(msg, "get"):
        return msg.get("tool_calls") or []
    return getattr(msg, "tool_calls", None) or []


def _parse_tool_calls(raw_tool_calls: list) -> list[ToolCall]:
    """Convert Ollama tool call objects to our ToolCall dataclass."""
    result: list[ToolCall] = []
    for tc in raw_tool_calls:
        if hasattr(tc, "get"):
            fn = tc.get("function", {})
            name = fn.get("name", "") if hasattr(fn, "get") else getattr(fn, "name", "")
            args = fn.get("arguments", {}) if hasattr(fn, "get") else getattr(fn, "arguments", {})
        else:
            fn = getattr(tc, "function", None)
            name = getattr(fn, "name", "") if fn else ""
            args = getattr(fn, "arguments", {}) if fn else {}

        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}

        result.append(ToolCall(id=str(uuid.uuid4()), name=name, arguments=args))
    return result


class OllamaLLM(BaseLLM):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1") -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    @property
    def provider_name(self) -> str:
        return "ollama"

    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def _prepare_messages(self, messages: list[dict]) -> list[dict]:
        """Ollama's Pydantic model requires tool_call arguments as dict, not JSON string."""
        result = []
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                new_tcs = []
                for tc in msg["tool_calls"]:
                    fn = dict(tc.get("function", {}))
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            fn["arguments"] = json.loads(args)
                        except json.JSONDecodeError:
                            fn["arguments"] = {}
                    new_tcs.append({**tc, "function": fn})
                result.append({**msg, "tool_calls": new_tcs})
            else:
                result.append(msg)
        return result

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> LLMResponse:
        import ollama as ollama_lib

        client = ollama_lib.AsyncClient(host=self.base_url)

        all_messages: list[dict] = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(self._prepare_messages(messages))

        kwargs: dict = {"model": self.model, "messages": all_messages}
        if tools and _TOOLS_ENABLED:
            kwargs["tools"] = tools

        response = await client.chat(**kwargs)
        msg = getattr(response, "message", response) if not hasattr(response, "get") else response.get("message", {})

        return LLMResponse(
            content=_msg_content(msg),
            tool_calls=_parse_tool_calls(_msg_tool_calls(msg)),
            model=self.model,
        )

    async def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream tokens from Ollama."""
        import ollama as ollama_lib

        client = ollama_lib.AsyncClient(host=self.base_url)

        all_messages: list[dict] = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(self._prepare_messages(messages))

        kwargs: dict = {"model": self.model, "messages": all_messages, "stream": True}
        if tools and _TOOLS_ENABLED:
            kwargs["tools"] = tools

        if not _TOOLS_ENABLED and tools:
            logger.debug("Ollama tools disabled (OLLAMA_TOOLS_ENABLED=false) — responding without tool schemas")

        async for part in await client.chat(**kwargs):
            msg = getattr(part, "message", None)
            token = _msg_content(msg)
            done = getattr(part, "done", False)
            raw_tool_calls = _msg_tool_calls(msg)

            if token:
                yield StreamChunk(delta=token, model=self.model)

            if done:
                yield StreamChunk(tool_calls=_parse_tool_calls(raw_tool_calls), done=True, model=self.model)
                break
