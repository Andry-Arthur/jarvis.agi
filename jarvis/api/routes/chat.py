"""REST chat endpoint (non-streaming). WebSocket streaming is in ws.py."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from jarvis.core.agent import Agent

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    provider: str | None = None


class ChatResponse(BaseModel):
    reply: str
    model: str = ""


def get_agent() -> Agent:
    from jarvis.api.main import app_state

    return app_state["agent"]


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest, agent: Agent = Depends(get_agent)):
    try:
        reply = await agent.run(
            req.message,
            history=req.history,
            provider=req.provider,
        )
        return ChatResponse(reply=reply)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/health")
async def health():
    return {"status": "ok"}
