"""
listening.py
------------
SOUL's ears: turns recorded sound into text using faster-whisper.

It does not guess. It checks how sure Whisper is. If it is unsure it
listens again with a more accurate model, and if it is still unsure it
asks you to repeat. Your words are never logged, only sizes, scores and time.
"""

import io
import re
import time

from backend.logging_config import get_logger

log = get_logger("listening")

# ---------- Settings you can change ----------

FAST_MODEL = "base"      # first listen (quick)
CAREFUL_MODEL = "small"  # second listen when the first is unsure (more accurate)

WHISPER_LANGUAGE = "en"  # use None if you mix Hindi and English words

# Confidence needed to accept the words (about -0.1 = very sure, -1.0 = unsure).
# These numbers are a starting guess. Raise toward -0.4 to be stricter.
CONFIDENT_ENOUGH = -0.6

# Turn the second listen on or off.
SECOND_LISTEN = True

MAX_AUDIO_BYTES = 10 * 1024 * 1024

_models = {}


class ListeningError(Exception):
    """Raised when SOUL cannot understand a recording."""


def _get_model(size: str = FAST_MODEL):
    """Load a Whisper model once, then reuse it."""
    if size not in _models:
        try:
            from faster_whisper import WhisperModel

            started = time.time()
            log.info("Loading Whisper model | size=%s", size)
            _models[size] = WhisperModel(size, device="cpu", compute_type="int8")
            log.info("Whisper loaded | size=%s | %.1fs", size, time.time() - started)
        except Exception as error:
            log.warning("Whisper load failed | error=%s", type(error).__name__)
            raise ListeningError("I could not start my hearing.") from error
    return _models[size]


def preload() -> None:
    """Load the fast model in the background when the server starts."""
    try:
        _get_model(FAST_MODEL)
    except ListeningError:
        pass  # already logged


def _normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", text.lower()))


def _listen_once(size: str, audio_bytes: bytes):
    """Return (text, confidence) from one model. Confidence is avg log-probability."""
    model = _get_model(size)
    try:
        segments, _info = model.transcribe(
            io.BytesIO(audio_bytes),
            language=WHISPER_LANGUAGE,
            beam_size=5,
            temperature=0.0,                 # no random retries
            condition_on_previous_text=False,
            vad_filter=False,
        )
        parts = list(segments)
    except Exception as error:
        log.warning("Transcribe failed | error=%s", type(error).__name__)
        raise ListeningError("I could not understand that recording.") from error

    text = " ".join(p.text.strip() for p in parts).strip()
    if not parts or not text:
        return "", 0.0
    total = sum(max(p.end - p.start, 0.01) for p in parts)
    confidence = sum(p.avg_logprob * max(p.end - p.start, 0.01) for p in parts) / total
    return text, confidence


def transcribe(audio_bytes: bytes) -> str:
    """Turn recorded sound into text, only when sure."""
    if not audio_bytes:
        raise ListeningError("The recording was empty.")
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise ListeningError("The recording is too long.")

    started = time.time()
    text, score = _listen_once(FAST_MODEL, audio_bytes)
    log.info("Listen 1 | model=%s | chars=%d | score=%.2f", FAST_MODEL, len(text), score)

    if not text or score >= CONFIDENT_ENOUGH:
        log.info("Heard something | chars=%d | %.2fs", len(text), time.time() - started)
        return text

    if SECOND_LISTEN:
        text2, score2 = _listen_once(CAREFUL_MODEL, audio_bytes)
        log.info("Listen 2 | model=%s | chars=%d | score=%.2f", CAREFUL_MODEL, len(text2), score2)
        if text2 and (score2 >= CONFIDENT_ENOUGH or _normalize(text) == _normalize(text2)):
            log.info("Heard something | chars=%d | %.2fs", len(text2), time.time() - started)
            return text2

    log.info("Not sure what was said | %.2fs", time.time() - started)
    raise ListeningError("I am not sure I heard that right. Please say it again.")