"""Emotional intelligence — detect user mood from voice tone using librosa.

Detects: calm, happy, sad, angry, anxious, excited, neutral.
JARVIS adapts its response style based on detected emotion.

Install: pip install librosa
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_SAMPLE_RATE = 16_000
_EMOTION_LABELS = ["neutral", "calm", "happy", "sad", "angry", "fearful", "disgust", "surprised"]

# Tone-to-style mapping: how JARVIS adjusts its response
_STYLE_MAP = {
    "neutral":   "normal",
    "calm":      "relaxed and informative",
    "happy":     "enthusiastic and celebratory",
    "sad":       "empathetic and gentle",
    "angry":     "calm and de-escalating",
    "fearful":   "reassuring and clear",
    "anxious":   "reassuring and structured",
    "surprised": "explanatory",
    "excited":   "matching energy, enthusiastic",
    "disgust":   "neutral and professional",
}


class EmotionDetector:
    """Analyzes audio to detect emotional state using prosodic features."""

    def __init__(self) -> None:
        self._model = None
        self._last_emotion = "neutral"
        self._last_confidence = 0.0

    def _ensure_model(self) -> bool:
        if self._model is not None:
            return True
        try:
            # Try loading a pre-trained speech emotion model
            # Using a simple rule-based prosodic analysis as fallback
            self._model = "prosodic"  # marker — using feature-based approach
            return True
        except Exception as exc:
            logger.warning("Emotion model unavailable: %s", exc)
            return False

    def _extract_features(self, audio: np.ndarray) -> dict:
        """Extract prosodic features from audio using librosa."""
        try:
            import librosa  # type: ignore[import]

            # Pitch (F0) — correlates with emotion
            pitches, magnitudes = librosa.piptrack(
                y=audio.astype(np.float32), sr=_SAMPLE_RATE
            )
            pitch_values = pitches[magnitudes > magnitudes.mean()]
            mean_pitch = float(np.mean(pitch_values)) if len(pitch_values) > 0 else 0.0
            pitch_std = float(np.std(pitch_values)) if len(pitch_values) > 0 else 0.0

            # Energy (RMS)
            rms = librosa.feature.rms(y=audio.astype(np.float32))[0]
            mean_energy = float(np.mean(rms))
            energy_std = float(np.std(rms))

            # Speech rate (zero crossing rate as proxy)
            zcr = librosa.feature.zero_crossing_rate(audio.astype(np.float32))[0]
            mean_zcr = float(np.mean(zcr))

            # MFCC variance (voice quality)
            mfccs = librosa.feature.mfcc(
                y=audio.astype(np.float32), sr=_SAMPLE_RATE, n_mfcc=13
            )
            mfcc_std = float(np.mean(np.std(mfccs, axis=1)))

            return {
                "mean_pitch": mean_pitch,
                "pitch_std": pitch_std,
                "mean_energy": mean_energy,
                "energy_std": energy_std,
                "mean_zcr": mean_zcr,
                "mfcc_std": mfcc_std,
            }
        except ImportError:
            logger.warning("librosa not installed — emotion detection unavailable.")
            return {}
        except Exception as exc:
            logger.debug("Feature extraction failed: %s", exc)
            return {}

    def _rule_based_classify(self, features: dict) -> tuple[str, float]:
        """Rule-based emotion classification from prosodic features."""
        if not features:
            return "neutral", 0.5

        pitch = features.get("mean_pitch", 0)
        pitch_std = features.get("pitch_std", 0)
        energy = features.get("mean_energy", 0)
        energy_std = features.get("energy_std", 0)

        # High energy + high pitch variation → excited/angry
        if energy > 0.05 and pitch_std > 50:
            if pitch > 250:
                return "excited", 0.7
            return "angry", 0.65

        # High energy + stable pitch → confident/happy
        if energy > 0.04 and pitch_std < 30:
            return "happy", 0.6

        # Low energy + low pitch → sad/calm
        if energy < 0.015:
            if pitch < 150:
                return "sad", 0.65
            return "calm", 0.6

        # High pitch variation + moderate energy → anxious
        if pitch_std > 40 and 0.02 < energy < 0.05:
            return "anxious", 0.55

        return "neutral", 0.8

    def detect(self, audio: np.ndarray) -> tuple[str, float]:
        """Detect emotion from a 16kHz float32 audio array.

        Returns: (emotion_label, confidence)
        """
        if not self._ensure_model():
            return "neutral", 0.5

        features = self._extract_features(audio)
        emotion, confidence = self._rule_based_classify(features)

        self._last_emotion = emotion
        self._last_confidence = confidence
        logger.debug("Emotion detected: %s (%.2f)", emotion, confidence)
        return emotion, confidence

    def get_response_style(self, emotion: Optional[str] = None) -> str:
        """Return the recommended response style for the detected emotion."""
        em = emotion or self._last_emotion
        return _STYLE_MAP.get(em, "normal")

    def get_system_prompt_suffix(self, emotion: Optional[str] = None) -> str:
        """Return a system prompt addition to adapt JARVIS's tone."""
        em = emotion or self._last_emotion
        style = self.get_response_style(em)
        if em == "neutral":
            return ""
        return (
            f"\n\nEmotion context: The user appears to be {em}. "
            f"Respond in a {style} manner."
        )

    @property
    def last_emotion(self) -> str:
        return self._last_emotion

    @property
    def last_confidence(self) -> float:
        return self._last_confidence
