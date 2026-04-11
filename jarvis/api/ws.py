"""WebSocket handler for real-time streaming agent responses.

Protocol (JSON messages):

Client → Server:
  {"type": "message", "content": "...", "history": [...], "provider": "openai"}
  {"type": "ping"}
  {"type": "tts_toggle", "enabled": true}
  {"type": "plan", "goal": "...", "history": [...]}
  {"type": "process_file", "path": "...","question": "..."}

Server → Client:
  {"type": "chunk",       "delta": "...", "model": "..."}   ← streaming token
  {"type": "tool_call",   "name": "...", "args": {...}}
  {"type": "tool_result", "name": "...", "result": "..."}
  {"type": "done",        "content": "...", "model": "..."}
  {"type": "audio",       "data": "<base64 mp3>"}
  {"type": "error",       "content": "..."}
  {"type": "plan_event",  ...}
  {"type": "notification","title": "...", "body": "...", "kind": "...", "timestamp": "..."}
  {"type": "pong"}
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


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

            if msg_type != "message":
                continue

            user_content = payload.get("content", "").strip()
            if not user_content:
                continue

            history = payload.get("history", [])
            provider = payload.get("provider")

            # True streaming: emit tokens as they arrive
            final_content = ""
            async for event in agent.stream(user_content, history=history, provider=provider):
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
