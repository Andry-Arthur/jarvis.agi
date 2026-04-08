"""Speaker identification/diarization using resemblyzer.

Enables JARVIS to recognize the user's voice versus other speakers,
and support per-speaker memory and preferences.

Install: pip install resemblyzer
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_PROFILE_DIR = Path(os.getenv("SPEAKER_PROFILE_DIR", ".jarvis/speakers"))
_SAMPLE_RATE = 16_000
_SIMILARITY_THRESHOLD = float(os.getenv("SPEAKER_SIMILARITY_THRESHOLD", "0.75"))


class SpeakerIdentifier:
    """Identifies speakers by comparing voice embeddings."""

    def __init__(self) -> None:
        self._encoder = None
        self._profiles: dict[str, np.ndarray] = {}  # name → embedding
        self._load_profiles()

    def _ensure_encoder(self) -> None:
        if self._encoder is not None:
            return
        try:
            from resemblyzer import VoiceEncoder  # type: ignore[import]

            self._encoder = VoiceEncoder()
            logger.info("Speaker encoder loaded.")
        except ImportError:
            logger.warning(
                "resemblyzer not installed — speaker identification disabled. "
                "Install with: pip install resemblyzer"
            )

    def _load_profiles(self) -> None:
        """Load saved speaker embeddings from disk."""
        _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        for profile_file in _PROFILE_DIR.glob("*.json"):
            try:
                data = json.loads(profile_file.read_text())
                self._profiles[data["name"]] = np.array(data["embedding"])
                logger.debug("Loaded speaker profile: %s", data["name"])
            except Exception as exc:
                logger.warning("Could not load speaker profile %s: %s", profile_file, exc)

    def _save_profile(self, name: str, embedding: np.ndarray) -> None:
        """Persist a speaker embedding to disk."""
        _PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        profile_file = _PROFILE_DIR / f"{name}.json"
        profile_file.write_text(
            json.dumps({"name": name, "embedding": embedding.tolist()})
        )

    def enroll(self, name: str, audio_samples: list[np.ndarray]) -> bool:
        """Enroll a new speaker by averaging embeddings from multiple audio samples.

        Args:
            name: Speaker name/ID.
            audio_samples: List of 16kHz float32 numpy arrays (each >= 1.6s).

        Returns:
            True on success.
        """
        self._ensure_encoder()
        if self._encoder is None:
            return False
        try:
            from resemblyzer import preprocess_wav  # type: ignore[import]

            embeddings = []
            for sample in audio_samples:
                wav = preprocess_wav(sample, source_sr=_SAMPLE_RATE)
                emb = self._encoder.embed_utterance(wav)
                embeddings.append(emb)

            mean_embedding = np.mean(embeddings, axis=0)
            self._profiles[name] = mean_embedding
            self._save_profile(name, mean_embedding)
            logger.info("Enrolled speaker: %s", name)
            return True
        except Exception as exc:
            logger.error("Speaker enrollment failed: %s", exc)
            return False

    def identify(self, audio: np.ndarray) -> Optional[str]:
        """Identify the speaker in an audio clip.

        Returns the speaker name with the highest cosine similarity, or None
        if no profile exceeds the similarity threshold.
        """
        self._ensure_encoder()
        if self._encoder is None or not self._profiles:
            return None
        try:
            from resemblyzer import preprocess_wav  # type: ignore[import]

            wav = preprocess_wav(audio, source_sr=_SAMPLE_RATE)
            embedding = self._encoder.embed_utterance(wav)

            best_name = None
            best_score = -1.0
            for name, profile_emb in self._profiles.items():
                score = float(
                    np.dot(embedding, profile_emb)
                    / (np.linalg.norm(embedding) * np.linalg.norm(profile_emb))
                )
                if score > best_score:
                    best_score = score
                    best_name = name

            if best_score >= _SIMILARITY_THRESHOLD:
                logger.debug(
                    "Speaker identified as '%s' (score %.3f)", best_name, best_score
                )
                return best_name
            logger.debug("Speaker unknown (best score %.3f < %.3f)", best_score, _SIMILARITY_THRESHOLD)
            return None
        except Exception as exc:
            logger.error("Speaker identification failed: %s", exc)
            return None

    @property
    def known_speakers(self) -> list[str]:
        return list(self._profiles.keys())

    def delete_profile(self, name: str) -> bool:
        if name in self._profiles:
            del self._profiles[name]
            profile_file = _PROFILE_DIR / f"{name}.json"
            if profile_file.exists():
                profile_file.unlink()
            logger.info("Deleted speaker profile: %s", name)
            return True
        return False
