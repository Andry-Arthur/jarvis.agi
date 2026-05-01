"""Async WebSocket client: pushes desktop sensor events to the JARVIS API."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

# region agent debug log
def _dbg(hypothesis_id: str, location: str, message: str, data: dict | None = None) -> None:
    try:
        import json

        payload = {
            "sessionId": "5ebe47",
            "runId": "pre-fix",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }
        with open("debug-5ebe47.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass


# endregion


def _queue_get_nonblocking(q: queue.Queue[list[dict[str, Any]]]) -> list[dict[str, Any]] | None:
    try:
        return q.get(timeout=0.2)
    except queue.Empty:
        return None


async def run_multimodal_bridge(
    ws_url: str,
    camera_index: int = 0,
    *,
    enable_mic: bool = True,
    fps_cap: float = 15.0,
) -> None:
    """Connect to ws_url and stream multimodal batches until disconnected."""
    import websockets  # type: ignore[import]

    from jarvis.multimodal.desktop_capture import (
        run_audio_emotion_loop,
        run_capture_loop,
    )

    out_q: queue.Queue[list[dict[str, Any]]] = queue.Queue(maxsize=32)
    stop_event = threading.Event()

    def on_cam_err(msg: str) -> None:
        logger.error("Camera error: %s", msg)
        try:
            out_q.put_nowait(
                [
                    {
                        "kind": "calibration",
                        "message": f"camera_error: {msg}",
                        "ts": time.time(),
                        "source_id": "desktop_bridge",
                    }
                ]
            )
        except queue.Full:
            pass

    cap_thread = threading.Thread(
        target=run_capture_loop,
        kwargs={
            "camera_index": camera_index,
            "fps_cap": fps_cap,
            "out_q": out_q,
            "stop_event": stop_event,
            "on_error": on_cam_err,
        },
        daemon=True,
        name="jarvis-multimodal-capture",
    )
    cap_thread.start()

    mic_thread = None
    if enable_mic and os.getenv("MULTIMODAL_MIC_ENABLED", "true").lower() in (
        "1",
        "true",
        "yes",
    ):
        mic_thread = threading.Thread(
            target=run_audio_emotion_loop,
            kwargs={
                "out_q": out_q,
                "stop_event": stop_event,
                "interval_s": float(os.getenv("MULTIMODAL_EMOTION_INTERVAL_S", "2.0")),
            },
            daemon=True,
            name="jarvis-multimodal-mic",
        )
        mic_thread.start()

    try:
        _dbg(
            "H10",
            "jarvis/multimodal/ws_bridge.py:run_multimodal_bridge",
            "Connecting websocket",
            {"ws_url": ws_url},
        )
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:

            async def sender() -> None:
                loop = asyncio.get_event_loop()
                while not stop_event.is_set():
                    batch = await loop.run_in_executor(None, _queue_get_nonblocking, out_q)
                    if batch is None:
                        await asyncio.sleep(0.02)
                        continue
                    payload = {"type": "multimodal_batch", "events": batch}
                    await ws.send(json.dumps(payload))

            async def recv_loop() -> None:
                try:
                    async for _msg in ws:
                        pass
                except Exception as exc:
                    logger.debug("Multimodal bridge recv ended: %s", exc)

            await asyncio.gather(sender(), recv_loop())
    except Exception as exc:
        _dbg(
            "H11",
            "jarvis/multimodal/ws_bridge.py:run_multimodal_bridge",
            "WebSocket connect/send failed",
            {"ws_url": ws_url, "exc": repr(exc)},
        )
        logger.exception("Multimodal bridge failed: %s", exc)
    finally:
        stop_event.set()
        cap_thread.join(timeout=3.0)
        if mic_thread:
            mic_thread.join(timeout=3.0)
