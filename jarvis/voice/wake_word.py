"""Wake word detection using openWakeWord.

Default model: "hey_jarvis" (pre-trained, downloaded automatically).
Custom models: supply a path to an .onnx file via WAKE_WORD_MODEL env var or
               train one at https://openwakeword.com.

The audio stream stays open continuously via listen_forever() so there is no
stop/restart overhead between activations.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import AsyncGenerator, Callable

import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000
CHUNK_FRAMES = 1_280  # 80 ms — required by openWakeWord


class WakeWordDetector:
    """Listens continuously for the wake word in a background thread."""

    def __init__(
        self,
        model_path: str = "",
        threshold: float = 0.5,
    ) -> None:
        """
        Args:
            model_path: Path to a custom .onnx model, or empty string to use
                        the built-in "hey_jarvis" pre-trained model.
            threshold:  Detection confidence threshold (0–1).
        """
        self.model_path = model_path
        self.threshold = threshold
        self._model = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None

    def _load_model(self) -> None:
        """Load and cache the wake word model (called once per instance)."""
        if self._model is not None:
            return

        import openwakeword
        from openwakeword.model import Model

        if self.model_path:
            logger.info("Loading custom wake word model: %s", self.model_path)
            self._model = Model(wakeword_models=[self.model_path], inference_framework="onnx")
        else:
            logger.info("Downloading/loading hey_jarvis wake word model…")
            openwakeword.utils.download_models()
            self._model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")

    def _run_detection(self, on_detected: Callable[[], None]) -> None:
        import sounddevice as sd

        self._load_model()
        logger.info("Wake word detection active — say 'Hey Jarvis'")

        def audio_callback(indata: np.ndarray, frames: int, time, status) -> None:
            audio_int16 = (np.squeeze(indata) * 32767).astype(np.int16)
            predictions = self._model.predict(audio_int16)

            for model_name, score in predictions.items():
                if score >= self.threshold:
                    logger.info("Wake word detected! (model=%s, score=%.3f)", model_name, score)
                    self._model.reset()
                    if self._loop and self._loop.is_running():
                        self._loop.call_soon_threadsafe(on_detected)
                    break

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=CHUNK_FRAMES,
            callback=audio_callback,
        ):
            while self._running:
                sd.sleep(100)

    def start(self, on_detected: Callable[[], None]) -> None:
        if self._running:
            return
        self._running = True
        self._loop = asyncio.get_event_loop()
        self._thread = threading.Thread(
            target=self._run_detection,
            args=(on_detected,),
            daemon=True,
            name="jarvis-wake-word",
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    async def listen_forever(self) -> AsyncGenerator[None, None]:
        """Async generator — yields each time the wake word is detected.

        Keeps the audio stream open continuously, so there is zero
        stop/restart overhead between activations.
        """
        queue: asyncio.Queue = asyncio.Queue()
        self._loop = asyncio.get_event_loop()

        self.start(on_detected=lambda: self._loop.call_soon_threadsafe(queue.put_nowait, None))
        try:
            while True:
                await queue.get()
                yield
        finally:
            self.stop()

    async def wait_for_wake_word(self) -> None:
        """Async helper: block until the wake word is detected once."""
        async for _ in self.listen_forever():
            return
