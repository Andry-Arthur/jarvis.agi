"""Multimodal desktop sensor status and dependency checks."""

from __future__ import annotations

import os

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/multimodal", tags=["multimodal"])


class MultimodalStatusResponse(BaseModel):
    enabled: bool
    fusion_window_s: float
    max_context_chars: int
    broadcast_hz: float
    desktop_dependencies: dict
    message: str


@router.get("/status", response_model=MultimodalStatusResponse)
async def get_multimodal_status() -> MultimodalStatusResponse:
    """Return env flags and whether OpenCV/MediaPipe are importable (for desktop bridge)."""
    from jarvis.multimodal.desktop_capture import check_desktop_dependencies

    enabled = os.getenv("MULTIMODAL_ENABLED", "false").lower() in ("1", "true", "yes")
    fusion_window = float(os.getenv("MULTIMODAL_FUSION_WINDOW_S", "20"))
    max_ctx = int(os.getenv("MULTIMODAL_MAX_CONTEXT_CHARS", "1200"))
    bhz = float(os.getenv("MULTIMODAL_BROADCAST_HZ", "5"))
    deps = check_desktop_dependencies()
    msg = "Multimodal context injection is " + ("on" if enabled else "off")
    if enabled and not deps.get("ok"):
        msg += " — install opencv + mediapipe to run the desktop bridge."
    return MultimodalStatusResponse(
        enabled=enabled,
        fusion_window_s=fusion_window,
        max_context_chars=max_ctx,
        broadcast_hz=bhz,
        desktop_dependencies=deps,
        message=msg,
    )
