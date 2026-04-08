"""Text-to-Speech using Microsoft Edge's free neural voices via edge-tts."""

from __future__ import annotations

import asyncio
import io
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

DEFAULT_VOICE = "en-US-GuyNeural"


class TextToSpeech:
    """Async TTS engine wrapping edge-tts with optional local playback."""

    def __init__(self, voice: str = DEFAULT_VOICE) -> None:
        self.voice = voice
        self._pygame_init = False

    def _ensure_pygame(self) -> None:
        if not self._pygame_init:
            import pygame

            pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=512)
            self._pygame_init = True

    async def synthesize(self, text: str) -> bytes:
        """Return raw MP3 bytes for the given text."""
        import edge_tts

        communicate = edge_tts.Communicate(text, voice=self.voice)
        audio_chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_chunks.append(chunk["data"])
        return b"".join(audio_chunks)

    async def speak(self, text: str) -> None:
        """Synthesize and play audio through the system speakers (blocking until done)."""
        import pygame

        self._ensure_pygame()
        audio_bytes = await self.synthesize(text)

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.05)
        finally:
            pygame.mixer.music.unload()
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    async def speak_in_background(self, text: str) -> asyncio.Task:
        """Start playback as a background task and return it."""
        return asyncio.create_task(self.speak(text))

    @staticmethod
    async def list_voices() -> list[dict]:
        """Return all available Edge TTS voices."""
        import edge_tts

        voices = await edge_tts.list_voices()
        return [{"name": v["Name"], "locale": v["Locale"], "gender": v["Gender"]} for v in voices]
