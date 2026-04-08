"""LLM Router — selects and falls back between providers with retry/backoff."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import AsyncGenerator

from jarvis.llm.base import BaseLLM, LLMResponse, StreamChunk

logger = logging.getLogger(__name__)

# Rate-limit / transient errors that warrant a retry
_RETRYABLE = (ConnectionError, TimeoutError, OSError)
_MAX_RETRIES = 2
_BACKOFF_BASE = 1.5  # seconds


async def _with_backoff(coro_factory, name: str):
    """Call an async factory function with exponential backoff on transient errors."""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            return await coro_factory()
        except _RETRYABLE as exc:
            if attempt == _MAX_RETRIES:
                raise
            wait = _BACKOFF_BASE ** attempt
            logger.warning(
                "Provider '%s' transient error (attempt %d/%d): %s — retrying in %.1fs",
                name, attempt + 1, _MAX_RETRIES + 1, exc, wait,
            )
            await asyncio.sleep(wait)
    raise RuntimeError("unreachable")


class LLMRouter:
    """Routes LLM requests to the configured provider, falling back as needed."""

    def __init__(self) -> None:
        self._providers: dict[str, BaseLLM] = {}
        self._order: list[str] = []
        self._default: str = ""

    # ------------------------------------------------------------------
    # Builder helpers
    # ------------------------------------------------------------------

    def register(self, name: str, provider: BaseLLM, *, default: bool = False) -> "LLMRouter":
        self._providers[name] = provider
        if name not in self._order:
            self._order.append(name)
        if default or not self._default:
            self._default = name
        return self

    @classmethod
    def from_env(cls) -> "LLMRouter":
        """Build a router from environment variables / settings."""
        from jarvis.llm.anthropic_llm import AnthropicLLM
        from jarvis.llm.ollama_llm import OllamaLLM
        from jarvis.llm.openai_llm import OpenAILLM

        router = cls()

        default_provider = os.getenv("DEFAULT_LLM", "openai")
        default_model = os.getenv("DEFAULT_MODEL", "")

        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            model = default_model if default_provider == "openai" and default_model else "gpt-4o"
            router.register(
                "openai",
                OpenAILLM(api_key=openai_key, model=model),
                default=(default_provider == "openai"),
            )

        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        if anthropic_key:
            model = (
                default_model
                if default_provider == "anthropic" and default_model
                else "claude-opus-4-5"
            )
            router.register(
                "anthropic",
                AnthropicLLM(api_key=anthropic_key, model=model),
                default=(default_provider == "anthropic"),
            )

        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1")
        if default_model and default_provider == "ollama":
            ollama_model = default_model
        router.register(
            "ollama",
            OllamaLLM(base_url=ollama_url, model=ollama_model),
            default=(default_provider == "ollama"),
        )

        return router

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def get(self, name: str | None = None) -> BaseLLM:
        """Return a specific provider or the default."""
        target = name or self._default
        if target not in self._providers:
            raise KeyError(
                f"Provider '{target}' not registered. Available: {list(self._providers)}"
            )
        return self._providers[target]

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        provider: str | None = None,
    ) -> LLMResponse:
        """Chat using the specified provider, falling back down the list on failure."""
        order = (
            [provider] + [p for p in self._order if p != provider]
            if provider
            else self._order
        )

        last_error: Exception | None = None
        for name in order:
            llm = self._providers.get(name)
            if llm is None:
                continue
            try:
                logger.debug("Routing to provider: %s", name)
                return await _with_backoff(
                    lambda llm=llm: llm.chat(messages, tools=tools, system=system), name
                )
            except Exception as exc:
                logger.warning("Provider '%s' failed: %s — trying next", name, exc)
                last_error = exc

        raise RuntimeError(
            f"All LLM providers failed. Last error: {last_error}"
        ) from last_error

    async def stream_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        provider: str | None = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream tokens from the best available provider."""
        order = (
            [provider] + [p for p in self._order if p != provider]
            if provider
            else self._order
        )

        for name in order:
            llm = self._providers.get(name)
            if llm is None:
                continue
            try:
                logger.debug("Streaming via provider: %s", name)
                async for chunk in llm.stream_chat(messages, tools=tools, system=system):
                    yield chunk
                return
            except Exception as exc:
                logger.warning(
                    "Provider '%s' stream failed: %s — trying next", name, exc
                )

        yield StreamChunk(delta="[Error: all LLM providers failed]", done=True)

    @property
    def available_providers(self) -> list[str]:
        return list(self._providers)
