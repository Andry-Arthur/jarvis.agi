"""WebSocket handler for real-time streaming agent responses.

Protocol (JSON messages):

Client → Server:
  {"type": "message", "content": "...", "history": [...], "provider": "openai"}
  {"type": "ping"}

Server → Client:
  {"type": "tool_call",   "name": "...", "args": {...}}
  {"type": "tool_result", "name": "...", "result": "..."}
  {"type": "done",        "content": "...", "model": "..."}
  {"type": "audio",       "data": "<base64 mp3>"}
  {"type": "error",       "content": "..."}
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


async def handle_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    logger.info("WebSocket client connected: %s", websocket.client)

    from jarvis.api.main import app_state

    agent = app_state["agent"]
    tts_voice = os.getenv("TTS_VOICE", "en-US-GuyNeural")
    tts_enabled = True

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)
            msg_type = payload.get("type", "message")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type != "message":
                continue

            user_content = payload.get("content", "").strip()
            if not user_content:
                continue

            history = payload.get("history", [])
            provider = payload.get("provider")

            # Stream agent events
            final_content = ""
            async for event in agent.stream(user_content, history=history, provider=provider):
                await websocket.send_json(event.to_dict())
                if event.kind == "done":
                    final_content = event.data.get("content", "")

            # Optionally synthesise and stream TTS audio
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
