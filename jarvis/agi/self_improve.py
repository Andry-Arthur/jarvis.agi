"""Self-improvement loop — JARVIS identifies capability gaps and proposes new tools.

The loop:
1. Monitors which tasks fail or require manual workarounds.
2. Asks the LLM to propose a new Tool class to fill the gap.
3. Presents the proposed code to the user for review.
4. On approval, saves and hot-loads the new tool into the plugin system.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_PROPOSAL_SYSTEM = """You are JARVIS's self-improvement engine. 
Given a description of a capability that JARVIS is missing, write a new Python Tool class.

Requirements:
1. Subclass `jarvis.core.tools.Tool`
2. Set `name`, `description`, and `parameters` class attributes
3. Implement `async def execute(self, **kwargs) -> str`
4. Handle all exceptions and return a descriptive error string instead of raising
5. Import all dependencies inside the `execute` method (lazy imports)

Output ONLY the Python code, no explanations.
"""


@dataclass
class ToolProposal:
    capability: str
    code: str
    tool_name: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "pending"  # "pending" | "approved" | "rejected" | "installed"


class SelfImprovementLoop:
    """Identifies gaps and proposes new tools with user approval."""

    def __init__(self, agent, registry, plugin_loader=None) -> None:
        self.agent = agent
        self.registry = registry
        self.plugin_loader = plugin_loader
        self._gap_log: list[dict] = []
        self._proposals: list[ToolProposal] = []

    def log_gap(self, user_request: str, failure_reason: str) -> None:
        """Record a failed request as a capability gap."""
        self._gap_log.append({
            "request": user_request,
            "reason": failure_reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        logger.info("Capability gap logged: %s", user_request[:60])

    async def propose_tool(self, capability: str) -> ToolProposal:
        """Ask the LLM to write a new tool for the described capability."""
        messages = [
            {
                "role": "user",
                "content": f"Write a JARVIS Tool class for this capability: {capability}",
            }
        ]
        response = await self.agent.llm.chat(messages, system=_PROPOSAL_SYSTEM)
        code = response.content.strip()

        # Extract tool name from code
        tool_name = "custom_tool"
        for line in code.split("\n"):
            if 'name = "' in line or "name = '" in line:
                tool_name = line.split("=")[1].strip().strip("\"'")
                break

        proposal = ToolProposal(capability=capability, code=code, tool_name=tool_name)
        self._proposals.append(proposal)
        logger.info("Tool proposal generated: %s", tool_name)
        return proposal

    async def install_proposal(
        self, proposal: ToolProposal, approval_required: bool = True
    ) -> bool:
        """Install a proposed tool into the plugin system.

        If approval_required=True (default), the caller must set proposal.status='approved'
        before calling this method.
        """
        if approval_required and proposal.status != "approved":
            logger.warning(
                "Tool '%s' not approved — skipping installation.", proposal.tool_name
            )
            return False

        plugin_name = f"ai_generated_{proposal.tool_name}"
        plugin_dir = Path(f".jarvis/plugins/{plugin_name}")
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Write the tool code
        (plugin_dir / "tools.py").write_text(proposal.code, encoding="utf-8")

        # Write the manifest
        import json
        manifest = {
            "name": plugin_name,
            "version": "1.0.0",
            "description": f"AI-generated tool for: {proposal.capability[:80]}",
            "author": "JARVIS Self-Improvement",
            "tools_module": "tools",
        }
        (plugin_dir / "plugin.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        # Hot-load into registry
        if self.plugin_loader:
            from jarvis.plugins.loader import PluginManifest
            mf = PluginManifest.from_file(plugin_dir / "plugin.json")
            tools = self.plugin_loader.load_tools(mf)
            self.registry.register_many(tools)
            logger.info(
                "Installed AI-generated tool '%s' (%d tool(s) loaded)",
                proposal.tool_name, len(tools),
            )

        proposal.status = "installed"
        return True

    def get_gaps(self) -> list[dict]:
        return list(self._gap_log)

    def get_proposals(self) -> list[dict]:
        return [
            {
                "capability": p.capability,
                "tool_name": p.tool_name,
                "status": p.status,
                "created_at": p.created_at,
            }
            for p in self._proposals
        ]
