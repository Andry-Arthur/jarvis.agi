"""Speech-to-Text using faster-whisper (local, no FFmpeg required)."""

from __future__ import annotations

import logging
import os

import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000
CHUNK_FRAMES = 1_280  # 80 ms @ 16 kHz


class SpeechToText:
    """Wraps faster-whisper for local transcription."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load(self) -> None:
        if self._model is not None:
            return
        from faster_whisper import WhisperModel

        logger.info("Loading Whisper model '%s' on %s…", self.model_size, self.device)
        self._model = WhisperModel(
            self.model_size, device=self.device, compute_type=self.compute_type
        )
        logger.info("Whisper model loaded.")

    def transcribe(self, audio: np.ndarray, language: str = "en") -> str:
        """Transcribe a float32 numpy array (16 kHz, mono) to text."""
        self._load()
        segments, _ = self._model.transcribe(
            audio,
            beam_size=5,
            language=language,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
        )
        return " ".join(s.text.strip() for s in segments).strip()

    def transcribe_file(self, path: str, language: str = "en") -> str:
        """Transcribe any audio file that ffmpeg can decode (WebM, MP4, WAV, MP3, etc.).

        faster-whisper passes the path directly to ffmpeg, so soundfile is not
        involved and WebM / Opus recordings from the browser are handled natively.
        """
        import json, time
        self._load()
        # #region agent log
        with open('debug-cd92b8.log', 'a') as _f:
            _f.write(json.dumps({"sessionId":"cd92b8","timestamp":int(time.time()*1000),"location":"stt.py:transcribe_file","message":"transcribing file","data":{"path":path},"hypothesisId":"H1"}) + '\n')
        # #endregion
        segments, _ = self._model.transcribe(
            path,
            beam_size=5,
            language=language,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
        )
        result = " ".join(s.text.strip() for s in segments).strip()
        # #region agent log
        with open('debug-cd92b8.log', 'a') as _f:
            _f.write(json.dumps({"sessionId":"cd92b8","timestamp":int(time.time()*1000),"location":"stt.py:transcribe_file","message":"transcription result","data":{"result":result},"hypothesisId":"H1"}) + '\n')
        # #endregion
        return result

    def record_until_silence(
        self,
        silence_threshold: float = 0.01,
        silence_duration_s: float = 1.5,
        max_duration_s: float = 30.0,
    ) -> np.ndarray:
        """
        Record from the default microphone until `silence_duration_s` seconds
        of continuous silence is detected, up to `max_duration_s`.

        Returns a float32 numpy array at SAMPLE_RATE.
        """
        import sounddevice as sd

        silent_chunks_needed = int(silence_duration_s * SAMPLE_RATE / CHUNK_FRAMES)
        max_chunks = int(max_duration_s * SAMPLE_RATE / CHUNK_FRAMES)

        chunks: list[np.ndarray] = []
        silent_count = 0
        has_speech = False

        logger.debug("Recording… speak now.")

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=CHUNK_FRAMES,
        ) as stream:
            while len(chunks) < max_chunks:
                frame, _ = stream.read(CHUNK_FRAMES)
                frame = np.squeeze(frame)
                chunks.append(frame)

                rms = float(np.sqrt(np.mean(frame**2)))
                if rms < silence_threshold:
                    silent_count += 1
                    if has_speech and silent_count >= silent_chunks_needed:
                        break
                else:
                    has_speech = True
                    silent_count = 0

        audio = np.concatenate(chunks) if chunks else np.zeros(CHUNK_FRAMES, dtype="float32")
        logger.debug("Recorded %.2f s of audio.", len(audio) / SAMPLE_RATE)
        return audio

    async def record_and_transcribe(
        self,
        silence_threshold: float = 0.01,
        silence_duration_s: float = 1.5,
    ) -> str:
        """Record from mic until silence, then transcribe. Runs blocking IO in executor."""
        import asyncio

        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(
            None,
            lambda: self.record_until_silence(
                silence_threshold=silence_threshold,
                silence_duration_s=silence_duration_s,
            ),
        )
        return await loop.run_in_executor(None, self.transcribe, audio)
