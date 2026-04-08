"""Ollama local LLM provider.

Requires Ollama running at OLLAMA_BASE_URL (default http://localhost:11434).
Tool calling works with models that support it (llama3.1, mistral-nemo, etc.).
"""

from __future__ import annotations

import json
import logging
import uuid

import httpx

from jarvis.llm.base import BaseLLM, LLMResponse, ToolCall

logger = logging.getLogger(__name__)


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

        # Ollama uses OpenAI-compatible tool format for supported models
        kwargs: dict = {"model": self.model, "messages": all_messages}
        if tools:
            kwargs["tools"] = tools

        response = await client.chat(**kwargs)
        msg = response["message"]

        tool_calls: list[ToolCall] = []
        raw_tool_calls = msg.get("tool_calls") or []
        for tc in raw_tool_calls:
            fn = tc.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            tool_calls.append(
                ToolCall(
                    id=str(uuid.uuid4()),
                    name=fn.get("name", ""),
                    arguments=args,
                )
            )

        return LLMResponse(
            content=msg.get("content", "") or "",
            tool_calls=tool_calls,
            model=self.model,
        )
