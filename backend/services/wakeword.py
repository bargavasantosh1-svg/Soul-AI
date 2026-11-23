"""
wakeword.py
-----------
SOUL's wake word listener ("Hey SOUL") using Whisper.

It watches the microphone. When you start talking and then pause, it
transcribes that short clip on this laptop and wakes if it hears "soul"
near the start. Nothing is saved and nothing leaves the laptop.
Your words are never written to the log.

Test it from the SOUL folder with:
    python -m backend.services.wakeword
Press Ctrl+C to stop.
"""

import re
import threading
import time
from collections import deque

import numpy as np
import sounddevice as sd

from backend.logging_config import get_logger
from backend.services.listening import ListeningError, _get_model

log = get_logger("wakeword")

# ---------- Settings you can change ----------

# Words Whisper may write when you say "SOUL" (accents change the spelling).
WAKE_WORDS = {
    "soul", "sol", "sole", "seoul", "soulle", "sould", "soal", "sool",
    "sold", "sull", "sul", "seol", "soulful", "soulless", "sowl", "sool",
    "so", "sal", "sell", "cool",
}

# The wake word must appear within the first this-many words.
WAKE_WITHIN_WORDS = 3

# Quietest level counted as speech (0 to 32767). Lower = more sensitive.
MIN_LEVEL = 250

# How much louder than the room noise speech must be.
NOISE_MULTIPLIER = 4

# Stop the clip after this much quiet (seconds).
SILENCE_SECONDS = 0.7

# Longest clip to check (seconds). Wake phrases are short.
MAX_CLIP_SECONDS = 6

# Ignore clips with less speech than this (seconds).
MIN_SPEECH_SECONDS = 0.3

SAMPLE_RATE = 16000
BLOCK = 1600  # 0.1 second of sound per step
SILENCE_BLOCKS = int(SILENCE_SECONDS * 10)
MAX_BLOCKS = int(MAX_CLIP_SECONDS * 10)
MIN_SPEECH_BLOCKS = int(MIN_SPEECH_SECONDS * 10)

# Set this to pause listening (for example while SOUL speaks or you record a command).
paused = threading.Event()


class WakeWordError(Exception):
    """Raised when the wake word listener cannot start."""


def find_wake(text: str):
    """Return (heard_wake_word, command_after_it)."""
    words = re.findall(r"[a-z']+", text.lower())
    for index, word in enumerate(words[:WAKE_WITHIN_WORDS]):
        if word in WAKE_WORDS:
            rest = words[index + 1:]
            # A real command needs at least two words after "SOUL".
            command = " ".join(rest) if len(rest) >= 2 else ""
            return True, command
    return False, ""


def _transcribe_clip(clip_int16: np.ndarray) -> str:
    """Turn a short clip into text with Whisper."""
    model = _get_model()
    audio = clip_int16.astype(np.float32) / 32768.0
    segments, _info = model.transcribe(
        audio,
        language="en",
        beam_size=1,
        condition_on_previous_text=False,
        vad_filter=False,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()


def listen_forever(on_wake, debug: bool = False, stop_event=None) -> None:
    """Listen to the microphone and call on_wake(command) when SOUL is called.

    command is "" if you only said "SOUL", or the rest of the sentence.
    """
    try:
        _get_model()
    except ListeningError as error:
        raise WakeWordError("I could not start my hearing.") from error

    log.info("Wake word listening | word=soul")
    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=BLOCK
        ) as stream:
            # Learn how noisy the room is (first second)
            levels = []
            for _ in range(10):
                block, _overflow = stream.read(BLOCK)
                levels.append(float(np.sqrt(np.mean(block.astype(np.float32) ** 2))))
            noise = float(np.mean(levels))

            preroll = deque(maxlen=3)  # keeps the start of your first word
            clip = []
            speaking = False
            silent = 0
            speech_blocks = 0
            last_print = 0.0

            while not (stop_event and stop_event.is_set()):
                block, _overflow = stream.read(BLOCK)
                block = block.reshape(-1)

                if paused.is_set():
                    preroll.clear()
                    clip = []
                    speaking = False
                    continue

                level = float(np.sqrt(np.mean(block.astype(np.float32) ** 2)))
                threshold = max(MIN_LEVEL, noise * NOISE_MULTIPLIER)

                if debug and time.time() - last_print > 1.0:
                    last_print = time.time()
                    print(f"  level={level:6.0f}  threshold={threshold:6.0f}")

                if not speaking:
                    preroll.append(block)
                    if level > threshold:
                        speaking = True
                        clip = list(preroll)
                        speech_blocks = 1
                        silent = 0
                    else:
                        noise = 0.97 * noise + 0.03 * level  # slowly follow the room
                    continue

                clip.append(block)
                if level > threshold:
                    speech_blocks += 1
                    silent = 0
                else:
                    silent += 1

                if silent >= SILENCE_BLOCKS or len(clip) >= MAX_BLOCKS:
                    heard_clip = np.concatenate(clip)
                    enough_speech = speech_blocks >= MIN_SPEECH_BLOCKS
                    clip = []
                    speaking = False
                    preroll.clear()
                    if not enough_speech:
                        continue

                    started = time.time()
                    try:
                        text = _transcribe_clip(heard_clip)
                    except Exception as error:
                        log.warning("Wake check failed | error=%s", type(error).__name__)
                        continue

                    woke, command = find_wake(text)
                    log.info(
                        "Wake check | chars=%d | woke=%s | %.2fs",
                        len(text), woke, time.time() - started,
                    )
                    if debug:
                        print(f'  heard: "{text}"  ->  {"WAKE" if woke else "ignored"}')
                    if woke:
                        on_wake(command)
    except sd.PortAudioError as error:
        log.warning("Microphone error | error=%s", type(error).__name__)
        raise WakeWordError("I could not open the microphone.") from error


if __name__ == "__main__":
    print("Loading Whisper... (a few seconds)")

    def show(command: str) -> None:
        if command:
            print(f'>>> WOKE with a command: "{command}"')
        else:
            print(">>> WOKE (just the name)")

    try:
        print('Ready. Say "Hey SOUL" or "Hey SOUL, what time is it". Ctrl+C to stop.')
        listen_forever(show, debug=True)
    except WakeWordError as error:
        print("Wake word test failed:", error)
    except KeyboardInterrupt:
        print("Stopped.")