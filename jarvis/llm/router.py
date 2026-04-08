"""LLM Router — selects and falls back between providers."""

from __future__ import annotations

import logging
import os

from jarvis.llm.base import BaseLLM, LLMResponse

logger = logging.getLogger(__name__)


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
            raise KeyError(f"Provider '{target}' not registered. Available: {list(self._providers)}")
        return self._providers[target]

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        system: str | None = None,
        provider: str | None = None,
    ) -> LLMResponse:
        """Chat using the specified provider, falling back down the list on failure."""
        order = [provider] + [p for p in self._order if p != provider] if provider else self._order

        last_error: Exception | None = None
        for name in order:
            llm = self._providers.get(name)
            if llm is None:
                continue
            try:
                logger.debug("Routing to provider: %s", name)
                return await llm.chat(messages, tools=tools, system=system)
            except Exception as exc:
                logger.warning("Provider '%s' failed: %s — trying next", name, exc)
                last_error = exc

        raise RuntimeError(
            f"All LLM providers failed. Last error: {last_error}"
        ) from last_error

    @property
    def available_providers(self) -> list[str]:
        return list(self._providers)
