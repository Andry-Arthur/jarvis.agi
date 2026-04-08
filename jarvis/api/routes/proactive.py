"""REST endpoints for proactive agent notifications and plan execution."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from jarvis.core.proactive import notification_bus

logger = logging.getLogger(__name__)
router = APIRouter(tags=["proactive"])


class NotificationResponse(BaseModel):
    title: str
    body: str
    timestamp: str
    kind: str


class PlanRequest(BaseModel):
    goal: str
    history: list[dict] | None = None


@router.get("/notifications", response_model=list[NotificationResponse])
async def get_notifications(limit: int = 20) -> list[NotificationResponse]:
    """Return recent proactive notifications."""
    history = notification_bus.get_history(limit=limit)
    return [NotificationResponse(**n) for n in history]


@router.post("/plan")
async def execute_plan(request: PlanRequest):
    """Execute a multi-step plan and return streaming events."""
    from fastapi.responses import StreamingResponse
    import json

    from jarvis.api.main import app_state
    from jarvis.core.planner import Planner

    agent = app_state.get("agent")
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not available")

    planner = Planner(agent=agent)

    async def event_stream():
        async for event in planner.execute(request.goal, history=request.history):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/proactive/run")
async def run_proactive(prompt: str, title: str = "JARVIS"):
    """Manually trigger a proactive task."""
    from jarvis.api.main import app_state
    from jarvis.core.proactive import ProactiveAgent

    agent = app_state.get("agent")
    scheduler = app_state.get("scheduler")
    if not agent or not scheduler:
        raise HTTPException(status_code=503, detail="Agent not available")

    proactive = ProactiveAgent(agent=agent, scheduler=scheduler)
    notification = await proactive.run_now(prompt=prompt, title=title)
    return {"title": notification.title, "body": notification.body, "kind": notification.kind}
