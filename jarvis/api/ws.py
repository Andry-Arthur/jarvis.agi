"""WebSocket handler for real-time streaming agent responses.

Protocol (JSON messages):

Client → Server:
  {"type": "message", "content": "...", "history": [...], "provider": "openai"}
  {"type": "ping"}
  {"type": "tts_toggle", "enabled": true}
  {"type": "plan", "goal": "...", "history": [...]}
  {"type": "process_file", "path": "...","question": "..."}
  {"type": "multimodal_batch", "events": [{ "kind": "gesture", "label": "...", ... }, ...]}
  {"type": "multimodal_event", "kind": "emotion", ...}
  {"type": "multimodal_control", "action": "clear"|"calibrate", "message": "..."}

Server → Client:
  {"type": "chunk",       "delta": "...", "model": "..."}   ← streaming token
  {"type": "tool_call",   "name": "...", "args": {...}}
  {"type": "tool_result", "name": "...", "result": "..."}
  {"type": "done",        "content": "...", "model": "..."}
  {"type": "audio",       "data": "<base64 mp3>"}
  {"type": "error",       "content": "..."}
  {"type": "plan_event",  ...}
  {"type": "notification","title": "...", "body": "...", "kind": "...", "timestamp": "..."}
  {"type": "multimodal_state", "event_count": ..., "last_gesture": ..., ...}
  {"type": "pong"}
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


def _multimodal_enabled() -> bool:
    return os.getenv("MULTIMODAL_ENABLED", "false").lower() in ("1", "true", "yes")


async def broadcast_multimodal_state() -> None:
    """Push fused multimodal summary to all WS clients (rate-limited)."""
    from jarvis.api.main import app_state

    fusion = app_state.get("multimodal_fusion")
    bucket = app_state.get("multimodal_broadcast_bucket")
    clients: set[WebSocket] = app_state.setdefault("ws_clients", set())
    if not fusion or not bucket or not bucket.consume():
        return
    payload = {"type": "multimodal_state", **fusion.summary_dict(), "ts": time.time()}
    stale: list[WebSocket] = []
    for ws in list(clients):
        try:
            await ws.send_json(payload)
        except Exception:
            stale.append(ws)
    for ws in stale:
        clients.discard(ws)


async def broadcast_proactive_notification(notification) -> None:
    """Push a proactive Notification to all connected WebSocket clients (best-effort)."""
    from jarvis.api.main import app_state

    clients: set[WebSocket] = app_state.setdefault("ws_clients", set())
    payload = {
        "type": "notification",
        "title": notification.title,
        "body": notification.body,
        "kind": notification.kind,
        "timestamp": notification.timestamp,
    }
    stale: list[WebSocket] = []
    for ws in list(clients):
        try:
            await ws.send_json(payload)
        except Exception:
            stale.append(ws)
    for ws in stale:
        clients.discard(ws)


async def _get_multimodal_suffix() -> str | None:
    """Build optional system-prompt suffix from global multimodal fusion."""
    if not _multimodal_enabled():
        return None
    from jarvis.api.main import app_state

    fusion = app_state.get("multimodal_fusion")
    lock = app_state.get("multimodal_lock")
    if not fusion:
        return None
    if lock:
        async with lock:
            suf = fusion.get_context_suffix()
            return suf if suf else None
    suf = fusion.get_context_suffix()
    return suf if suf else None


async def _handle_multimodal_control(payload: dict) -> None:
    from jarvis.api.main import app_state
    from jarvis.multimodal.events import normalize_multimodal_event

    fusion = app_state.get("multimodal_fusion")
    lock = app_state.get("multimodal_lock")
    if not fusion or not lock:
        return
    action = str(payload.get("action", "")).strip()
    async with lock:
        if action == "clear":
            fusion.clear()
        elif action == "calibrate":
            msg = str(payload.get("message", "user calibrated"))[:256]
            ev = normalize_multimodal_event(
                {
                    "kind": "calibration",
                    "message": msg,
                    "ts": time.time(),
                }
            )
            if ev:
                fusion.ingest(ev)


async def _handle_multimodal_ingest(payload: dict, msg_type: str) -> None:
    from jarvis.api.main import app_state
    from jarvis.multimodal.events import (
        normalize_multimodal_event,
        normalize_multimodal_payload,
    )

    fusion = app_state.get("multimodal_fusion")
    lock = app_state.get("multimodal_lock")
    if not fusion or not lock:
        return

    if msg_type == "multimodal_event":
        inner = {k: v for k, v in payload.items() if k != "type"}
        raw_events: list = []
        ev = normalize_multimodal_event(inner)
        if ev:
            raw_events.append(ev)
    else:
        raw_events = normalize_multimodal_payload(payload)

    if not raw_events:
        return

    async with lock:
        for e in raw_events:
            fusion.ingest(e)


async def handle_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("WebSocket client connected: %s", websocket.client)

    from jarvis.api.main import app_state

    clients: set[WebSocket] = app_state.setdefault("ws_clients", set())
    clients.add(websocket)

    agent = app_state["agent"]
    tts_voice = os.getenv("TTS_VOICE", "en-US-AriaNeural")
    tts_enabled = True

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            msg_type = payload.get("type", "message")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type == "tts_toggle":
                tts_enabled = payload.get("enabled", True)
                continue

            if msg_type == "plan":
                goal = payload.get("goal", "").strip()
                if goal:
                    asyncio.create_task(
                        _handle_plan(websocket, agent, goal, payload.get("history", []))
                    )
                continue

            if msg_type == "process_file":
                path = payload.get("path", "")
                question = payload.get("question", "")
                if path:
                    asyncio.create_task(
                        _handle_file(websocket, agent, path, question)
                    )
                continue

            if msg_type == "multimodal_control" and _multimodal_enabled():
                await _handle_multimodal_control(payload)
                await broadcast_multimodal_state()
                continue

            if msg_type in ("multimodal_batch", "multimodal_event") and _multimodal_enabled():
                try:
                    await _handle_multimodal_ingest(payload, msg_type)
                    await broadcast_multimodal_state()
                except Exception as mm_exc:
                    logger.warning("Multimodal ingest failed (ignored): %s", mm_exc)
                continue

            if msg_type != "message":
                continue

            user_content = payload.get("content", "").strip()
            if not user_content:
                continue

            history = payload.get("history", [])
            provider = payload.get("provider")

            multimodal_suffix = await _get_multimodal_suffix()

            # True streaming: emit tokens as they arrive
            final_content = ""
            async for event in agent.stream(
                user_content,
                history=history,
                provider=provider,
                multimodal_suffix=multimodal_suffix,
            ):
                await websocket.send_json(event.to_dict())
                if event.kind == "done":
                    final_content = event.data.get("content", "")
                elif event.kind == "chunk":
                    final_content += event.data.get("delta", "")

            # Optionally synthesise TTS audio for the complete response
            if tts_enabled and final_content:
                asyncio.create_task(
                    _send_tts_audio(websocket, final_content, tts_voice)
                )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception as exc:
        logger.exception("WebSocket error")
        try:
            await websocket.send_json({"type": "error", "content": str(exc)})
        except Exception:
            pass
    finally:
        clients.discard(websocket)


async def _handle_plan(
    websocket: WebSocket, agent, goal: str, history: list
) -> None:
    """Execute a multi-step plan and stream events."""
    from jarvis.core.planner import Planner

    planner = Planner(agent=agent)
    try:
        async for event in planner.execute(goal, history=history):
            await websocket.send_json({"type": "plan_event", **event})
    except Exception as exc:
        await websocket.send_json({"type": "error", "content": str(exc)})


async def _handle_file(
    websocket: WebSocket, agent, path: str, question: str
) -> None:
    """Process a file and send the result."""
    from jarvis.agi.multimodal import MultimodalProcessor

    processor = MultimodalProcessor(llm_router=agent.llm)
    try:
        result = await processor.process_file(path, question=question)
        await websocket.send_json({"type": "done", "content": result, "model": "multimodal"})
    except Exception as exc:
        await websocket.send_json({"type": "error", "content": str(exc)})


async def _send_tts_audio(websocket: WebSocket, text: str, voice: str) -> None:
    """Synthesise TTS and send as a base64-encoded MP3 message."""
    try:
        from jarvis.voice.tts import TextToSpeech

        tts = TextToSpeech(voice=voice)
        audio_bytes = await tts.synthesize(text)
        b64 = base64.b64encode(audio_bytes).decode()
        await websocket.send_json({"type": "audio", "data": b64, "mime": "audio/mpeg"})
    except Exception as exc:
        logger.warning("TTS failed: %s", exc)
