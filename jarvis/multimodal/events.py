"""Multimodal WebSocket event validation and normalization."""

from __future__ import annotations

import time
from typing import Any

# Client → Server event kinds (single-event envelope or batch)
VALID_EVENT_KINDS = frozenset(
    {
        "gesture",
        "pose_state",
        "emotion",
        "attention",
        "audio_vad",
        "calibration",
    }
)


def _now_ts() -> float:
    return time.time()


def normalize_multimodal_event(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Validate and normalize one multimodal event dict. Returns None if invalid."""
    kind = raw.get("kind")
    if kind not in VALID_EVENT_KINDS:
        return None
    ts = raw.get("ts")
    if ts is None:
        ts = _now_ts()
    try:
        ts = float(ts)
    except (TypeError, ValueError):
        ts = _now_ts()

    confidence = raw.get("confidence")
    if confidence is not None:
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = None

    out: dict[str, Any] = {
        "kind": kind,
        "ts": ts,
        "source_id": str(raw.get("source_id", "default"))[:64],
    }
    if confidence is not None:
        out["confidence"] = confidence

    # Kind-specific optional fields
    if kind == "gesture":
        label = raw.get("label") or raw.get("gesture")
        if not label or not isinstance(label, str):
            return None
        out["label"] = label.strip()[:128]
        detail = raw.get("detail")
        if isinstance(detail, str):
            out["detail"] = detail[:500]

    elif kind == "pose_state":
        stance = raw.get("stance") or raw.get("label")
        if isinstance(stance, str):
            out["stance"] = stance[:128]

    elif kind == "emotion":
        label = raw.get("label") or raw.get("emotion")
        if isinstance(label, str):
            out["label"] = label.strip()[:64]

    elif kind == "attention":
        for key in ("engaged", "facing", "level"):
            if key in raw:
                out[key] = raw[key]

    elif kind == "audio_vad":
        speaking = raw.get("speaking")
        if speaking is not None:
            out["speaking"] = bool(speaking)
        level = raw.get("level")
        if level is not None:
            try:
                out["level"] = max(0.0, min(1.0, float(level)))
            except (TypeError, ValueError):
                pass

    elif kind == "calibration":
        msg = raw.get("message") or raw.get("detail")
        if isinstance(msg, str):
            out["message"] = msg[:256]

    return out


def normalize_multimodal_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize multimodal_batch body (events array)."""
    if payload.get("events"):
        events = payload["events"]
        if not isinstance(events, list):
            return []
        out: list[dict[str, Any]] = []
        for e in events:
            if isinstance(e, dict):
                n = normalize_multimodal_event(e)
                if n:
                    out.append(n)
        return out
    return []
