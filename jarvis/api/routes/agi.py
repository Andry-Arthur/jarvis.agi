"""REST endpoints for AGI frontier features."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["agi"])


# ── World Model ────────────────────────────────────────────────────────────────

@router.get("/world-model")
async def get_world_model():
    """Return the current world model context."""
    from jarvis.api.main import app_state
    from jarvis.agi.world_model import WorldModel

    world_model = app_state.get("world_model")
    if not world_model:
        world_model = WorldModel()
        app_state["world_model"] = world_model

    context = await world_model.get_context()
    return {"context": context or "World model is empty."}


# ── Self-Improvement ───────────────────────────────────────────────────────────

class GapRequest(BaseModel):
    capability: str


class ApprovalRequest(BaseModel):
    proposal_index: int


@router.post("/self-improve/propose")
async def propose_tool(request: GapRequest):
    """Ask JARVIS to propose a new tool for a described capability."""
    from jarvis.api.main import app_state
    from jarvis.agi.self_improve import SelfImprovementLoop

    agent = app_state.get("agent")
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not available")

    loop = app_state.setdefault(
        "self_improve",
        SelfImprovementLoop(agent=agent, registry=agent.tools),
    )
    proposal = await loop.propose_tool(request.capability)
    idx = len(loop._proposals) - 1
    return {
        "index": idx,
        "tool_name": proposal.tool_name,
        "code": proposal.code,
        "status": proposal.status,
    }


@router.post("/self-improve/approve/{proposal_index}")
async def approve_tool(proposal_index: int):
    """Approve and install a proposed tool."""
    from jarvis.api.main import app_state

    loop = app_state.get("self_improve")
    if not loop or proposal_index >= len(loop._proposals):
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal = loop._proposals[proposal_index]
    proposal.status = "approved"
    success = await loop.install_proposal(proposal, approval_required=True)
    return {"success": success, "tool_name": proposal.tool_name, "status": proposal.status}


@router.get("/self-improve/proposals")
async def list_proposals():
    from jarvis.api.main import app_state
    loop = app_state.get("self_improve")
    if not loop:
        return {"proposals": []}
    return {"proposals": loop.get_proposals()}


# ── Multimodal ────────────────────────────────────────────────────────────────

@router.post("/multimodal/process")
async def process_file(
    file: UploadFile,
    question: str = "",
):
    """Process an uploaded file (image, PDF, audio, screenshot) and return extracted content."""
    import os
    import tempfile

    from jarvis.api.main import app_state
    from jarvis.agi.multimodal import MultimodalProcessor

    agent = app_state.get("agent")
    processor = MultimodalProcessor(llm_router=agent.llm if agent else None)

    suffix = os.path.splitext(file.filename or "file.bin")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        result = await processor.process_file(tmp_path, question=question)
        return {"result": result, "filename": file.filename}
    finally:
        os.unlink(tmp_path)


# ── Emotion Detection ─────────────────────────────────────────────────────────

@router.get("/agi/emotion")
async def get_last_emotion():
    from jarvis.api.main import app_state
    detector = app_state.get("emotion_detector")
    if not detector:
        return {"emotion": "neutral", "confidence": 0.0, "style": "normal"}
    return {
        "emotion": detector.last_emotion,
        "confidence": detector.last_confidence,
        "style": detector.get_response_style(),
    }
