"""
api/voice.py
------------
POST /api/voice/speak    {"text": "Hello"}      -> an MP3 sound (SOUL speaks)
POST /api/voice/listen   audio file upload      -> {"text": "..."} (SOUL listens)
"""

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backend.logging_config import get_logger
from backend.services.listening import MAX_AUDIO_BYTES, ListeningError, transcribe
from backend.services.voice import VoiceError, synthesize

log = get_logger("api.voice")

router = APIRouter(prefix="/api/voice", tags=["voice"])


class SpeakRequest(BaseModel):
    """What the web page sends when it wants SOUL to speak."""

    text: str = Field(min_length=1, max_length=4000)


@router.post("/speak")
async def speak(request: SpeakRequest):
    """Turn text into an MP3 sound."""
    try:
        sound = await synthesize(request.text)
    except VoiceError as error:
        return JSONResponse(
            status_code=503,
            content={"error": "voice_unavailable", "detail": str(error)},
        )
    return Response(content=sound, media_type="audio/mpeg")


@router.post("/listen")
async def listen(audio: UploadFile = File(...)):
    """Turn a recording into text."""
    data = await audio.read(MAX_AUDIO_BYTES + 1)
    try:
        # Whisper is slow and blocking, so run it off the main thread.
        text = await run_in_threadpool(transcribe, data)
    except ListeningError as error:
        return JSONResponse(
            status_code=422,
            content={"error": "listening_failed", "detail": str(error)},
        )
    return {"text": text}   