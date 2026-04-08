"""Voice REST endpoints — TTS synthesis and STT transcription."""

from __future__ import annotations

import base64
import logging
import tempfile
import os

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])


class TTSRequest(BaseModel):
    text: str
    voice: str = "en-US-GuyNeural"


class TranscribeResponse(BaseModel):
    text: str


@router.post("/tts")
async def text_to_speech(req: TTSRequest):
    """Synthesise text to speech and return MP3 audio bytes."""
    from jarvis.voice.tts import TextToSpeech

    tts = TextToSpeech(voice=req.voice)
    try:
        audio_bytes = await tts.synthesize(req.text)
    except Exception as exc:
        logger.exception("TTS synthesis failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return StreamingResponse(
        iter([audio_bytes]),
        media_type="audio/mpeg",
        headers={"Content-Disposition": 'inline; filename="jarvis_tts.mp3"'},
    )


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(file: UploadFile = File(...)):
    """Transcribe an uploaded audio file (WebM, WAV, MP3, etc.) to text using Whisper."""
    import asyncio
    from jarvis.voice.stt import SpeechToText

    # Preserve the original file extension so faster-whisper/ffmpeg can detect the format
    suffix = os.path.splitext(file.filename or "recording.webm")[1] or ".webm"
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        loop = asyncio.get_event_loop()
        stt = SpeechToText(
            model_size=os.getenv("WHISPER_MODEL", "base"),
            device="cpu",
            compute_type="int8",
        )
        # Pass the file path directly to faster-whisper — it decodes via ffmpeg
        # and handles any format the browser sends (WebM/Opus, MP4, WAV, etc.)
        text = await loop.run_in_executor(None, stt.transcribe_file, tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    return TranscribeResponse(text=text)


@router.get("/voices")
async def list_voices():
    """Return all available Edge TTS voices."""
    from jarvis.voice.tts import TextToSpeech

    voices = await TextToSpeech.list_voices()
    return {"voices": voices}
