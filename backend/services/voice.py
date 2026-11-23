"""
voice.py
--------
SOUL's speaking voice (text to speech) using Edge TTS.

Edge TTS needs the internet. It turns text into an MP3 sound.
Later we will add listening (Whisper) to this same file.

Test it from the SOUL folder with:
    python -m backend.services.voice
You can also try another voice name:
    python -m backend.services.voice en-IN-NeerjaNeural
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import edge_tts

from backend.logging_config import get_logger

log = get_logger("voice")

# ---------- Settings you can change ----------

# The voice SOUL speaks with (British English, male, calm).
VOICE_NAME = "en-GB-RyanNeural"

# Speed. "+0%" is normal. "+20%" is faster. "-10%" is slower.
VOICE_RATE = "+15%"

# Pitch. "+0Hz" is normal. Keep the format: a sign, a number, then Hz.
VOICE_PITCH = "+0Hz"

# Volume. "+0%" is normal.
VOICE_VOLUME = "+0%"

# Never speak more than this many characters at once.
MAX_SPEAK_CHARS = 1000


class VoiceError(Exception):
    """Raised when SOUL cannot make a voice sound."""


async def synthesize(
    text: str,
    voice: str = VOICE_NAME,
    rate: str = VOICE_RATE,
    pitch: str = VOICE_PITCH,
    volume: str = VOICE_VOLUME,
) -> bytes:
    """Turn text into MP3 sound bytes."""
    text = (text or "").strip()
    if not text:
        raise VoiceError("There is no text to speak.")
    if len(text) > MAX_SPEAK_CHARS:
        text = text[:MAX_SPEAK_CHARS]

    audio = bytearray()
    try:
        communicate = edge_tts.Communicate(
            text, voice, rate=rate, pitch=pitch, volume=volume
        )
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio.extend(chunk["data"])
    except Exception as error:
        # We log only the error type, never the private text.
        log.warning("Voice failed | error=%s", type(error).__name__)
        raise VoiceError(
            "I could not make my voice. Check your internet connection."
        ) from error

    if not audio:
        raise VoiceError("The voice service returned no sound.")

    log.info("Voice ready | chars=%d | bytes=%d", len(text), len(audio))
    return bytes(audio)


def synthesize_blocking(text: str, voice: str = VOICE_NAME) -> bytes:
    """Same as synthesize(), for normal (non-async) code."""
    return asyncio.run(synthesize(text, voice))


def save_to_file(text: str, path: Path, voice: str = VOICE_NAME) -> Path:
    """Make the voice and save it as an MP3 file."""
    sound = synthesize_blocking(text, voice)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(sound)
    return path


if __name__ == "__main__":
    # A quick test: make a voice file and open it in your default player.
    chosen_voice = sys.argv[1] if len(sys.argv) > 1 else VOICE_NAME
    test_path = Path(tempfile.gettempdir()) / "soul_voice_test.mp3"
    try:
        save_to_file(
            "Yes, Bargav. I am SOUL, and my voice is working. "
            "Your battery is fine, and you have three reminders today.",
            test_path,
            chosen_voice,
        )
        print("Voice used:", chosen_voice)
        print("Voice file saved:", test_path)
        os.startfile(test_path)  # Windows only: opens the MP3
    except VoiceError as error:
        print("Voice test failed:", error)