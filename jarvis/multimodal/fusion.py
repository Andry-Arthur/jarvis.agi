"""Rolling-window fusion of multimodal signals into LLM context."""

from __future__ import annotations

import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MultimodalFusionState:
    """Keeps a short horizon of multimodal events and builds a system prompt suffix."""

    window_s: float = 20.0
    max_events: int = 80
    _events: deque[dict[str, Any]] = field(default_factory=deque)
    _calibration_note: str | None = None

    def __post_init__(self) -> None:
        self.window_s = float(os.getenv("MULTIMODAL_FUSION_WINDOW_S", str(self.window_s)))
        max_chars = int(os.getenv("MULTIMODAL_MAX_CONTEXT_CHARS", "1200"))
        self._max_context_chars = max(200, min(4000, max_chars))

    def clear(self) -> None:
        self._events.clear()
        self._calibration_note = None

    def ingest(self, event: dict[str, Any]) -> None:
        now = time.time()
        self._prune(now)
        self._events.append(event)
        if len(self._events) > self.max_events:
            self._events.popleft()
        if event.get("kind") == "calibration" and event.get("message"):
            self._calibration_note = str(event["message"])[:256]

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_s
        while self._events and float(self._events[0].get("ts", 0)) < cutoff:
            self._events.popleft()

    def get_context_suffix(self, now: float | None = None) -> str:
        """Compact description for system prompt injection."""
        now = now or time.time()
        self._prune(now)
        if not self._events and not self._calibration_note:
            return ""

        lines: list[str] = []
        if self._calibration_note:
            lines.append(f"Calibration: {self._calibration_note}")

        gestures: list[str] = []
        emotions: list[str] = []
        attention_summary: dict[str, Any] = {}
        pose_hints: list[str] = []
        vad_on = False

        for e in self._events:
            k = e.get("kind")
            if k == "gesture" and e.get("label"):
                conf = e.get("confidence")
                g = e["label"]
                if conf is not None:
                    g = f"{g} ({float(conf):.2f})"
                gestures.append(g)
            elif k == "emotion" and e.get("label"):
                emotions.append(str(e["label"]))
            elif k == "attention":
                if "engaged" in e:
                    attention_summary["engaged"] = e["engaged"]
                if "facing" in e:
                    attention_summary["facing"] = e["facing"]
                if "level" in e:
                    try:
                        attention_summary["level"] = float(e["level"])
                    except (TypeError, ValueError):
                        pass
            elif k == "pose_state" and e.get("stance"):
                pose_hints.append(str(e["stance"]))
            elif k == "audio_vad" and e.get("speaking"):
                vad_on = True

        if gestures:
            # last 5 unique order-preserving
            seen: set[str] = set()
            uniq: list[str] = []
            for g in gestures[-15:]:
                if g not in seen:
                    seen.add(g)
                    uniq.append(g)
            lines.append("Recent gestures: " + ", ".join(uniq[-5:]))

        if emotions:
            lines.append("Recent voice tone cues (emotion labels): " + emotions[-1])

        if pose_hints:
            lines.append("Body posture notes: " + ", ".join(pose_hints[-3:]))

        if attention_summary:
            parts = []
            if "engaged" in attention_summary:
                parts.append(f"engaged={attention_summary['engaged']}")
            if "facing" in attention_summary:
                parts.append(f"facing_camera={attention_summary['facing']}")
            if "level" in attention_summary:
                parts.append(f"attention_level={attention_summary['level']:.2f}")
            if parts:
                lines.append("Attention: " + "; ".join(parts))

        if vad_on:
            lines.append("Microphone: user appears to be speaking (VAD).")

        text = "\n".join(lines)
        if len(text) > self._max_context_chars:
            text = text[: self._max_context_chars] + "\n…(truncated)"

        return (
            "\n\nMultimodal context (last ~"
            + str(int(self.window_s))
            + "s, desktop sensors — use subtly, do not narrate unless asked):\n"
            + text
        )

    def summary_dict(self) -> dict[str, Any]:
        """UI / broadcast compact summary."""
        now = time.time()
        self._prune(now)
        last_gesture = None
        last_emotion = None
        attention = {}
        for e in reversed(self._events):
            if last_gesture is None and e.get("kind") == "gesture":
                last_gesture = e.get("label")
            if last_emotion is None and e.get("kind") == "emotion":
                last_emotion = e.get("label")
            if e.get("kind") == "attention":
                attention = {k: e.get(k) for k in ("engaged", "facing", "level") if k in e}
                break
        return {
            "event_count": len(self._events),
            "last_gesture": last_gesture,
            "last_emotion": last_emotion,
            "attention": attention,
            "window_s": self.window_s,
            "calibration": self._calibration_note,
        }
