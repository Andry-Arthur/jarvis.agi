"""Multi-step autonomous planner for JARVIS.

Uses a ReAct-style loop: decompose goal → execute subtasks → synthesize results.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

_PLANNER_SYSTEM = """You are JARVIS's planning module. Your job is to decompose complex goals 
into a numbered list of concrete subtasks that JARVIS can execute step by step.

When given a goal, respond ONLY with a JSON object in this exact format:
{
  "plan_title": "Brief title",
  "steps": [
    {"id": 1, "description": "First subtask", "tool_hint": "optional tool name"},
    {"id": 2, "description": "Second subtask", "tool_hint": "optional tool name"}
  ]
}

Keep steps concrete, actionable, and ordered. Maximum 10 steps."""

_SYNTHESIZER_SYSTEM = """You are JARVIS synthesizing the results of a multi-step plan.
Given the original goal and the results of each step, produce a clear, helpful summary 
for the user. Be concise but complete."""


@dataclass
class PlanStep:
    id: int
    description: str
    tool_hint: str = ""
    result: str = ""
    status: str = "pending"  # "pending" | "running" | "done" | "failed"


@dataclass
class Plan:
    title: str
    goal: str
    steps: list[PlanStep] = field(default_factory=list)
    status: str = "created"  # "created" | "running" | "done" | "failed"


class Planner:
    """Decomposes complex goals and orchestrates multi-step execution."""

    def __init__(self, agent) -> None:
        self.agent = agent

    async def decompose(self, goal: str) -> Plan:
        """Ask the LLM to break a goal into concrete steps."""
        import json

        messages = [{"role": "user", "content": f"Goal: {goal}"}]
        try:
            response = await self.agent.llm.chat(messages, system=_PLANNER_SYSTEM)
            # Parse JSON from the response
            content = response.content.strip()
            # Extract JSON if wrapped in code fences
            if "```" in content:
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            data = json.loads(content)
            steps = [
                PlanStep(
                    id=s["id"],
                    description=s["description"],
                    tool_hint=s.get("tool_hint", ""),
                )
                for s in data.get("steps", [])
            ]
            return Plan(title=data.get("plan_title", "Plan"), goal=goal, steps=steps)
        except Exception as exc:
            logger.error("Plan decomposition failed: %s", exc)
            # Fallback: single-step plan
            return Plan(
                title="Direct execution",
                goal=goal,
                steps=[PlanStep(id=1, description=goal)],
            )

    async def execute(
        self, goal: str, history: list[dict] | None = None
    ) -> AsyncGenerator[dict, None]:
        """Decompose and execute a plan, yielding status updates."""
        plan = await self.decompose(goal)
        plan.status = "running"
        yield {"type": "plan_created", "plan": plan.title, "steps": len(plan.steps)}

        step_results = []
        for step in plan.steps:
            step.status = "running"
            yield {
                "type": "step_start",
                "step_id": step.id,
                "description": step.description,
            }
            try:
                result = await self.agent.run(
                    step.description,
                    history=history,
                )
                step.result = result
                step.status = "done"
                step_results.append(f"Step {step.id} ({step.description}): {result}")
                yield {
                    "type": "step_done",
                    "step_id": step.id,
                    "result": result,
                }
            except Exception as exc:
                step.status = "failed"
                step.result = str(exc)
                step_results.append(f"Step {step.id} FAILED: {exc}")
                yield {
                    "type": "step_failed",
                    "step_id": step.id,
                    "error": str(exc),
                }

        # Synthesize final answer
        synthesis_prompt = (
            f"Original goal: {goal}\n\n"
            + "\n".join(step_results)
            + "\n\nProvide a helpful summary of what was accomplished."
        )
        try:
            summary = await self.agent.run(synthesis_prompt)
        except Exception as exc:
            summary = f"Plan completed with errors. {exc}"

        plan.status = "done"
        yield {"type": "plan_done", "summary": summary}

    async def run(self, goal: str, history: list[dict] | None = None) -> str:
        """Execute a plan and return the final synthesized answer."""
        final_summary = ""
        async for event in self.execute(goal, history=history):
            if event["type"] == "plan_done":
                final_summary = event["summary"]
        return final_summary
