"""Multimodal input processor — images, PDFs, audio files, and screenshots.

Supports:
  - Images: described via vision-capable LLM (GPT-4o, Claude claude-opus-4-5)
  - PDFs: text extraction via pypdf
  - Audio files: transcription via faster-whisper
  - Screenshots: OCR via pytesseract
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _encode_image(path: str) -> str:
    """Encode an image file to base64 string."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


class MultimodalProcessor:
    """Processes various input types and converts them to text or LLM-compatible format."""

    def __init__(self, llm_router=None, stt=None) -> None:
        self.llm = llm_router
        self.stt = stt

    async def process_image(
        self, image_path: str, question: str = "Describe this image in detail."
    ) -> str:
        """Send an image to a vision-capable LLM and get a description."""
        if self.llm is None:
            return "No LLM available for image processing."

        ext = Path(image_path).suffix.lower().lstrip(".")
        mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}
        mime = mime_map.get(ext, "jpeg")

        try:
            image_data = _encode_image(image_path)
            # Use OpenAI vision format
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/{mime};base64,{image_data}",
                                "detail": "high",
                            },
                        },
                        {"type": "text", "text": question},
                    ],
                }
            ]
            # Try OpenAI first (GPT-4o supports vision), then Anthropic Claude
            for provider in ["openai", "anthropic"]:
                try:
                    response = await self.llm.chat(messages, provider=provider)
                    return response.content
                except Exception:
                    continue
            return "Vision-capable LLM not available. Configure OpenAI or Anthropic."
        except Exception as exc:
            logger.error("process_image failed: %s", exc)
            return f"Error processing image: {exc}"

    async def process_pdf(self, pdf_path: str, max_chars: int = 10000) -> str:
        """Extract text from a PDF file."""
        try:
            import pypdf  # type: ignore[import]

            reader = pypdf.PdfReader(pdf_path)
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
            text = "\n".join(text_parts).strip()
            if len(text) > max_chars:
                text = text[:max_chars] + f"\n...[truncated — {len(text)} chars total]"
            return text
        except ImportError:
            return "pypdf not installed. Run: pip install pypdf"
        except Exception as exc:
            logger.error("process_pdf failed: %s", exc)
            return f"Error reading PDF: {exc}"

    async def process_audio_file(self, audio_path: str) -> str:
        """Transcribe an audio file using faster-whisper."""
        if self.stt is None:
            try:
                from jarvis.voice.stt import SpeechToText
                self.stt = SpeechToText()
            except Exception as exc:
                return f"STT not available: {exc}"

        try:
            import soundfile as sf

            audio, sr = sf.read(audio_path, dtype="float32")
            if sr != 16000:
                import librosa  # type: ignore[import]
                audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)

            return await self.stt.transcribe(audio)
        except Exception as exc:
            logger.error("process_audio_file failed: %s", exc)
            return f"Error transcribing audio: {exc}"

    async def process_screenshot(self, screenshot_path: str) -> str:
        """Extract text from a screenshot using OCR."""
        try:
            import pytesseract
            from PIL import Image

            tesseract_cmd = os.getenv("TESSERACT_CMD", "")
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

            img = Image.open(screenshot_path)
            text = pytesseract.image_to_string(img)
            return text.strip() or "(no text detected in screenshot)"
        except ImportError:
            return "pytesseract or Pillow not installed."
        except Exception as exc:
            logger.error("process_screenshot failed: %s", exc)
            return f"Error reading screenshot: {exc}"

    async def process_file(self, file_path: str, question: str = "") -> str:
        """Auto-detect file type and process it appropriately."""
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"):
            return await self.process_image(file_path, question or "Describe this image.")
        elif ext == ".pdf":
            text = await self.process_pdf(file_path)
            if question and self.llm:
                response = await self.llm.chat(
                    [{"role": "user", "content": f"Document:\n{text}\n\nQuestion: {question}"}]
                )
                return response.content
            return text
        elif ext in (".wav", ".mp3", ".flac", ".ogg", ".m4a"):
            return await self.process_audio_file(file_path)
        elif ext in (".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml"):
            text = path.read_text(encoding="utf-8", errors="replace")
            if question and self.llm:
                response = await self.llm.chat(
                    [{"role": "user", "content": f"File content:\n{text}\n\nQuestion: {question}"}]
                )
                return response.content
            return text
        else:
            return await self.process_screenshot(file_path)
