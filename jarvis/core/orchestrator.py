"""Multi-agent orchestrator for JARVIS.

Spawns specialist sub-agents with focused tool subsets and system prompts,
then aggregates their outputs through a coordinator.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from jarvis.core.tools import Tool, ToolRegistry
from jarvis.llm.router import LLMRouter

logger = logging.getLogger(__name__)


@dataclass
class SubAgentConfig:
    name: str
    system_prompt: str
    tool_names: list[str] = field(default_factory=list)  # Empty = all tools


_SUB_AGENTS: list[SubAgentConfig] = [
    SubAgentConfig(
        name="email_agent",
        system_prompt=(
            "You are an email specialist. Your job is to read, search, send, and organise "
            "emails. Always confirm before sending. Be concise."
        ),
        tool_names=["gmail_search", "gmail_read", "gmail_send", "gmail_archive"],
    ),
    SubAgentConfig(
        name="calendar_agent",
        system_prompt=(
            "You are a scheduling specialist. Manage calendar events, find free slots, "
            "and avoid conflicts. Always use ISO 8601 dates."
        ),
        tool_names=[
            "calendar_list_events",
            "calendar_create_event",
            "calendar_delete_event",
            "calendar_find_free_slot",
        ],
    ),
    SubAgentConfig(
        name="research_agent",
        system_prompt=(
            "You are a research specialist. Use web browsing and knowledge base tools to "
            "find information, summarise documents, and answer factual questions."
        ),
        tool_names=[
            "browser_navigate",
            "browser_extract_text",
            "kb_search",
            "drive_search",
            "drive_read_doc",
        ],
    ),
    SubAgentConfig(
        name="code_agent",
        system_prompt=(
            "You are a coding specialist. Write, execute, and debug Python code. "
            "Always explain what the code does before running it."
        ),
        tool_names=["execute_python", "execute_shell", "fs_read_file", "fs_write_file"],
    ),
    SubAgentConfig(
        name="media_agent",
        system_prompt=(
            "You are a media and entertainment specialist. Handle Spotify, YouTube, "
            "and other media-related requests."
        ),
        tool_names=[
            "spotify_play",
            "spotify_pause",
            "spotify_search_track",
            "spotify_add_to_queue",
            "youtube_search",
        ],
    ),
    SubAgentConfig(
        name="comms_agent",
        system_prompt=(
            "You are a communications specialist. Handle messaging across Discord, "
            "Telegram, Slack, WhatsApp, and Instagram."
        ),
        tool_names=[
            "discord_send_message",
            "telegram_send_message",
            "slack_send_message",
            "whatsapp_send_message",
            "instagram_send_dm",
        ],
    ),
]


_COORDINATOR_SYSTEM = """You are the JARVIS coordinator. You receive outputs from specialist 
sub-agents and synthesize them into a single, clear, helpful response for the user.
Be concise. Avoid repeating information. Format the output clearly."""


class Orchestrator:
    """Routes tasks to specialist sub-agents and aggregates results."""

    def __init__(self, llm_router: LLMRouter, tool_registry: ToolRegistry) -> None:
        self.llm = llm_router
        self.registry = tool_registry
        self._agents: dict[str, "Agent"] = {}
        self._build_agents()

    def _build_agents(self) -> None:
        from jarvis.core.agent import Agent

        for config in _SUB_AGENTS:
            # Build a restricted registry for this agent
            if config.tool_names:
                sub_registry = ToolRegistry()
                for tool_name in config.tool_names:
                    tool = self.registry._tools.get(tool_name)
                    if tool:
                        sub_registry.register(tool)
            else:
                sub_registry = self.registry

            self._agents[config.name] = Agent(
                llm_router=self.llm,
                tool_registry=sub_registry,
                max_iterations=5,
            )
            # Override system prompt
            self._agents[config.name]._system_prompt = config.system_prompt

        logger.info("Orchestrator: %d sub-agents ready", len(self._agents))

    def _route(self, message: str) -> list[str]:
        """Determine which sub-agents should handle this message."""
        msg_lower = message.lower()
        agents_to_use = []

        routing_rules = {
            "email_agent": ["email", "gmail", "inbox", "send mail", "unread"],
            "calendar_agent": ["calendar", "schedule", "event", "meeting", "appointment", "free slot"],
            "research_agent": ["search", "find", "lookup", "what is", "research", "browse", "website"],
            "code_agent": ["code", "script", "python", "run", "execute", "debug", "program"],
            "media_agent": ["play", "music", "spotify", "youtube", "video", "song", "playlist"],
            "comms_agent": ["message", "telegram", "discord", "slack", "whatsapp", "instagram", "dm"],
        }

        for agent_name, keywords in routing_rules.items():
            if any(kw in msg_lower for kw in keywords):
                agents_to_use.append(agent_name)

        # Default to all agents if no clear routing
        return agents_to_use or list(self._agents.keys())

    async def run(
        self,
        message: str,
        history: list[dict] | None = None,
        provider: str | None = None,
    ) -> str:
        """Route message to relevant sub-agents and synthesize the result."""
        from jarvis.core.agent import SYSTEM_PROMPT, Agent

        agent_names = self._route(message)
        logger.info("Orchestrator routing to: %s", agent_names)

        if len(agent_names) == 1:
            # Single agent — run directly
            agent = self._agents[agent_names[0]]
            return await agent.run(message, history=history, provider=provider)

        # Multiple agents — run in parallel and synthesize
        import asyncio

        tasks = {
            name: self._agents[name].run(message, history=history, provider=provider)
            for name in agent_names
            if name in self._agents
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        agent_outputs = []
        for name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                agent_outputs.append(f"[{name}] Error: {result}")
            elif result:
                agent_outputs.append(f"[{name}]\n{result}")

        if not agent_outputs:
            return "No sub-agents produced a result."

        # Synthesize
        synthesis_messages = [
            {
                "role": "user",
                "content": (
                    f"User request: {message}\n\n"
                    "Sub-agent outputs:\n"
                    + "\n\n".join(agent_outputs)
                    + "\n\nProvide a unified response."
                ),
            }
        ]
        try:
            response = await self.llm.chat(
                synthesis_messages, system=_COORDINATOR_SYSTEM, provider=provider
            )
            return response.content
        except Exception as exc:
            logger.error("Orchestrator synthesis failed: %s", exc)
            return "\n\n".join(agent_outputs)
