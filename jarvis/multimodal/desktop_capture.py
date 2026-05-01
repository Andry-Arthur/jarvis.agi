"""Local webcam + optional mic features for multimodal events (OpenCV + MediaPipe)."""

from __future__ import annotations

import logging
import os
import queue
import threading
import time
import urllib.request
from pathlib import Path
from collections import deque
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Landmark indices (MediaPipe Pose)
_L_SH, _R_SH = 11, 12
_L_EL, _R_EL = 13, 14
_L_WR, _R_WR = 15, 16
_L_HIP, _R_HIP = 23, 24


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


# region agent debug log
def _dbg(hypothesis_id: str, location: str, message: str, data: dict | None = None) -> None:
    # Never log secrets/PII here.
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


class GestureHeuristicClassifier:
    """Rule-based full-body / pose gestures from pose landmarks."""

    def __init__(self) -> None:
        self._lwx = deque(maxlen=12)
        self._rwx = deque(maxlen=12)
        self._last_emit = 0.0
        self._min_interval = float(os.getenv("MULTIMODAL_GESTURE_MIN_INTERVAL_S", "0.45"))

    def classify(
        self,
        landmarks: list[Any] | None,
        t: float | None = None,
    ) -> str | None:
        """Return gesture label or None."""
        if not landmarks or len(landmarks) < 25:
            return None
        t = t or time.time()
        if t - self._last_emit < self._min_interval:
            return None

        def pt(i: int) -> tuple[float, float, float]:
            p = landmarks[i]
            vis = getattr(p, "visibility", 1.0) or 0.0
            return (float(p.x), float(p.y), float(vis))

        ls, rs = pt(_L_SH), pt(_R_SH)
        lw, rw = pt(_L_WR), pt(_R_WR)
        le, re = pt(_L_EL), pt(_R_EL)
        lh, rh = pt(_L_HIP), pt(_R_HIP)

        if ls[2] < 0.4 or rs[2] < 0.4:
            return None

        # y increases downward; "above" shoulder means smaller y
        shoulder_y = min(ls[1], rs[1])
        both_hands_up = (
            lw[2] > 0.5
            and rw[2] > 0.5
            and lw[1] < shoulder_y - 0.06
            and rw[1] < shoulder_y - 0.06
        )
        if both_hands_up:
            self._last_emit = t
            return "attention_request"

        one_hand_raised = (
            (lw[2] > 0.5 and lw[1] < shoulder_y - 0.08 and rw[2] > 0.5 and rw[1] > shoulder_y)
            or (rw[2] > 0.5 and rw[1] < shoulder_y - 0.08 and lw[2] > 0.5 and lw[1] > shoulder_y)
        )
        if one_hand_raised:
            self._last_emit = t
            return "single_hand_up"

        # Arms crossed (approximate): wrists near opposite elbows / center
        cross = (
            lw[2] > 0.45
            and rw[2] > 0.45
            and _dist((lw[0], lw[1]), (rs[0], rs[1])) < 0.18
            and _dist((rw[0], rw[1]), (ls[0], ls[1])) < 0.18
        )
        if cross:
            self._last_emit = t
            return "pause"

        # Wave: horizontal oscillation of one wrist
        self._lwx.append(lw[0])
        self._rwx.append(rw[0])
        if len(self._lwx) >= 8 and lw[1] < lh[1] - 0.1:
            lx_var = max(self._lwx) - min(self._lwx)
            rx_var = max(self._rwx) - min(self._rwx)
            if max(lx_var, rx_var) > 0.22 and (lw[2] > 0.5 or rw[2] > 0.5):
                self._last_emit = t
                return "wave"

        # Pointing: arm extended forward — elbow angle wide, wrist away from shoulder
        def arm_extended(sw: tuple[float, float, float], ew: tuple[float, float, float], ww: tuple[float, float, float]) -> bool:
            if sw[2] < 0.4 or ew[2] < 0.4 or ww[2] < 0.4:
                return False
            # distance shoulder-wrist vs shoulder-elbow
            return _dist((sw[0], sw[1]), (ww[0], ww[1])) > 1.6 * _dist((sw[0], sw[1]), (ew[0], ew[1]))

        if arm_extended(ls, le, lw) or arm_extended(rs, re, rw):
            self._last_emit = t
            return "pointing"

        return None


def _try_import_cv2():
    try:
        import cv2  # type: ignore[import]

        return cv2
    except ImportError:
        return None


def _try_pose():
    try:
        import mediapipe as mp  # type: ignore[import]
        _dbg(
            "H1",
            "jarvis/multimodal/desktop_capture.py:_try_pose",
            "Imported mediapipe module",
            {
                "module_file": getattr(mp, "__file__", None),
                "module_version": getattr(mp, "__version__", None),
                "has_solutions": hasattr(mp, "solutions"),
                "dir_sample": [k for k in dir(mp) if k in ("solutions", "__version__", "python", "tasks")],
                "type": str(type(mp)),
            },
        )

        sols = getattr(mp, "solutions", None)
        if sols is None:
            _dbg(
                "H2",
                "jarvis/multimodal/desktop_capture.py:_try_pose",
                "mediapipe.solutions missing (name collision or bad install)",
                {"module_file": getattr(mp, "__file__", None)},
            )
            # Fallback: newer mediapipe builds (and some Python versions) may only ship `tasks`.
            try:
                from mediapipe.tasks.python import vision  # type: ignore[import]
                from mediapipe.tasks.python.core import base_options  # type: ignore[import]

                _dbg(
                    "H6",
                    "jarvis/multimodal/desktop_capture.py:_try_pose",
                    "Using mediapipe.tasks PoseLandmarker fallback",
                    {},
                )

                model_path = os.getenv(
                    "MULTIMODAL_POSE_MODEL",
                    str(Path(".jarvis/models/pose_landmarker_lite.task")),
                )
                model = Path(model_path)
                if not model.exists():
                    model.parent.mkdir(parents=True, exist_ok=True)
                    url = os.getenv(
                        "MULTIMODAL_POSE_MODEL_URL",
                        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
                    )
                    _dbg(
                        "H7",
                        "jarvis/multimodal/desktop_capture.py:_try_pose",
                        "Downloading PoseLandmarker model",
                        {"url": url, "dest": str(model)},
                    )
                    urllib.request.urlretrieve(url, str(model))  # noqa: S310 (known model URL)

                return ("tasks", vision, base_options, str(model))
            except Exception as exc:
                _dbg(
                    "H8",
                    "jarvis/multimodal/desktop_capture.py:_try_pose",
                    "mediapipe.tasks fallback unavailable",
                    {"exc": repr(exc)},
                )
                return None

        pose = getattr(sols, "pose", None)
        if pose is None:
            _dbg(
                "H3",
                "jarvis/multimodal/desktop_capture.py:_try_pose",
                "mediapipe.solutions.pose missing",
                {"solutions_type": str(type(sols)), "solutions_dir_sample": [k for k in dir(sols) if "pose" in k][:20]},
            )
            return None

        return ("solutions", pose)
    except ImportError:
        _dbg(
            "H4",
            "jarvis/multimodal/desktop_capture.py:_try_pose",
            "mediapipe import failed (ImportError)",
        )
        return None
    except Exception as exc:
        _dbg(
            "H5",
            "jarvis/multimodal/desktop_capture.py:_try_pose",
            "mediapipe import unexpected exception",
            {"exc": repr(exc)},
        )
        return None


def check_desktop_dependencies() -> dict[str, Any]:
    """Return availability flags for startup validation."""
    cv2 = _try_import_cv2()
    pose_mod = _try_pose()
    _dbg(
        "H1",
        "jarvis/multimodal/desktop_capture.py:check_desktop_dependencies",
        "Dependency check",
        {"opencv": cv2 is not None, "pose_mod": pose_mod is not None},
    )
    backend = None
    if isinstance(pose_mod, tuple) and pose_mod:
        backend = pose_mod[0]
    return {
        "opencv": cv2 is not None,
        "mediapipe_pose": pose_mod is not None,
        "mediapipe_backend": backend,
        "ok": cv2 is not None and pose_mod is not None,
        "message": (
            "Ready"
            if cv2 and pose_mod
            else "Install optional deps: pip install opencv-python-headless mediapipe"
        ),
    }


def run_capture_loop(
    camera_index: int,
    fps_cap: float,
    out_q: queue.Queue[list[dict[str, Any]]],
    stop_event: threading.Event,
    on_error: Callable[[str], None] | None = None,
) -> None:
    """Blocking loop: grab frames, emit multimodal event dicts (lists pushed to queue)."""
    cv2 = _try_import_cv2()
    pose_mod = _try_pose()
    if cv2 is None or pose_mod is None:
        msg = "opencv or mediapipe not installed"
        logger.error(msg)
        if on_error:
            on_error(msg)
        return

    classifier = GestureHeuristicClassifier()
    min_frame_interval = 1.0 / max(1.0, min(60.0, fps_cap))

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        msg = f"Cannot open camera index {camera_index}"
        logger.error(msg)
        if on_error:
            on_error(msg)
        return

    backend = pose_mod[0] if isinstance(pose_mod, tuple) else None
    _dbg(
        "H6",
        "jarvis/multimodal/desktop_capture.py:run_capture_loop",
        "Pose backend selected",
        {"backend": backend},
    )

    def emit_events_from_landmarks(lm: list[Any], now: float) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        label = classifier.classify(lm, t=now)
        if label:
            events.append(
                {
                    "kind": "gesture",
                    "label": label,
                    "confidence": 0.75,
                    "ts": now,
                    "source_id": "desktop_pose",
                }
            )
        # attention / facing heuristic from nose vs shoulders
        nose = lm[0]
        vis = getattr(nose, "visibility", 1.0) or 0.0
        if vis > 0.5:
            mid_sh_y = (lm[_L_SH].y + lm[_R_SH].y) / 2
            facing = nose.y < mid_sh_y + 0.15
            events.append(
                {
                    "kind": "attention",
                    "facing": facing,
                    "engaged": facing,
                    "level": float(max(0.0, min(1.0, 1.0 - abs(float(nose.x) - 0.5) * 2))),
                    "ts": now,
                    "source_id": "desktop_pose",
                }
            )
        hip_vis = getattr(lm[_L_HIP], "visibility", 0.0) or 0.0
        stance = "standing" if hip_vis > 0.4 else "unknown"
        events.append(
            {
                "kind": "pose_state",
                "stance": stance,
                "ts": now,
                "source_id": "desktop_pose",
            }
        )
        return events

    if backend == "solutions":
        pose_api = pose_mod[1]
        with pose_api.Pose(
            static_image_mode=False,
            model_complexity=int(os.getenv("MULTIMODAL_POSE_COMPLEXITY", "1")),
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        ) as pose:
            last_frame_t = 0.0
            while not stop_event.is_set():
                now = time.time()
                if now - last_frame_t < min_frame_interval:
                    time.sleep(0.002)
                    continue
                last_frame_t = now

                ok, frame = cap.read()
                if not ok:
                    logger.warning("Frame grab failed")
                    time.sleep(0.05)
                    continue

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                res = pose.process(rgb)
                if res.pose_landmarks:
                    events = emit_events_from_landmarks(res.pose_landmarks.landmark, now)
                else:
                    events = []

                if events:
                    try:
                        out_q.put(events, timeout=0.5)
                    except queue.Full:
                        logger.debug("Multimodal queue full, dropping frame batch")

    elif backend == "tasks":
        vision = pose_mod[1]
        base_options = pose_mod[2]
        model_path = pose_mod[3]
        try:
            options = vision.PoseLandmarkerOptions(
                base_options=base_options.BaseOptions(model_asset_path=model_path),
                running_mode=vision.RunningMode.VIDEO,
                num_poses=1,
            )
            landmarker = vision.PoseLandmarker.create_from_options(options)
        except Exception as exc:
            msg = f"PoseLandmarker init failed: {exc}"
            logger.error(msg)
            if on_error:
                on_error(msg)
            cap.release()
            return

        last_frame_t = 0.0
        frame_index = 0
        while not stop_event.is_set():
            now = time.time()
            if now - last_frame_t < min_frame_interval:
                time.sleep(0.002)
                continue
            last_frame_t = now

            ok, frame = cap.read()
            if not ok:
                logger.warning("Frame grab failed")
                time.sleep(0.05)
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            try:
                mp_image = vision.MPImage(image_format=vision.ImageFormat.SRGB, data=rgb)
                res = landmarker.detect_for_video(mp_image, int(now * 1000))
                lms = None
                if getattr(res, "pose_landmarks", None) and len(res.pose_landmarks) > 0:
                    lms = res.pose_landmarks[0]
                if lms:
                    events = emit_events_from_landmarks(lms, now)
                else:
                    events = []
            except Exception as exc:
                frame_index += 1
                if frame_index % 30 == 0:
                    _dbg(
                        "H9",
                        "jarvis/multimodal/desktop_capture.py:run_capture_loop",
                        "PoseLandmarker detect failed (sampled)",
                        {"exc": repr(exc)},
                    )
                events = []

            if events:
                try:
                    out_q.put(events, timeout=0.5)
                except queue.Full:
                    logger.debug("Multimodal queue full, dropping frame batch")

        try:
            landmarker.close()
        except Exception:
            pass

    else:
        msg = "Unknown mediapipe pose backend"
        logger.error(msg)
        if on_error:
            on_error(msg)

    cap.release()


def run_audio_emotion_loop(
    out_q: queue.Queue[list[dict[str, Any]]],
    stop_event: threading.Event,
    interval_s: float = 1.5,
) -> None:
    """Optional mic loop: prosodic emotion via EmotionDetector on short recordings."""
    try:
        import numpy as np
        import sounddevice as sd  # type: ignore[import]
    except ImportError:
        logger.info("sounddevice/numpy not available — skipping mic emotion loop")
        return

    from jarvis.agi.emotion import EmotionDetector

    detector = EmotionDetector()
    sr = 16000
    chunk_s = max(0.8, float(os.getenv("MULTIMODAL_AUDIO_CHUNK_S", "1.0")))

    while not stop_event.is_set():
        try:
            n_frames = int(sr * chunk_s)
            audio = sd.rec(n_frames, samplerate=sr, channels=1, dtype="float32")
            sd.wait()
            flat = np.squeeze(audio).astype("float32")
            em, conf = detector.detect(flat)
            out_q.put(
                [
                    {
                        "kind": "emotion",
                        "label": em,
                        "confidence": float(conf),
                        "ts": time.time(),
                        "source_id": "desktop_mic",
                    }
                ],
                timeout=0.5,
            )
        except queue.Full:
            pass
        except Exception as exc:
            logger.debug("Audio emotion chunk failed: %s", exc)
        stop_event.wait(timeout=interval_s)
