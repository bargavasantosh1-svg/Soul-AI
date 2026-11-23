"""
brain.py
--------
SOUL's brain. It talks to the AI model (Gemini through the OpenAI SDK)
and remembers the current conversation.
Other files use it like this:

    from backend.services.brain import brain
    reply = brain.chat("Hello")
"""

import threading
import time
from datetime import datetime

from openai import OpenAI

from backend.config import settings
from backend.exceptions import ConfigurationError, translate_openai_error
from backend.logging_config import get_logger

log = get_logger("brain")

# SOUL's personality. Change this text to change how SOUL talks.
# {now} is filled in with the real date and time on every message.
SYSTEM_PROMPT_TEMPLATE = """You are {assistant}, a personal AI assistant inspired by JARVIS.
Your owner is {user}. You live on his laptop and he mostly talks to you by voice.

Name rule:
- Use "{user}" only rarely, for example in a first greeting or when something is really important. Most replies should not contain his name.
- If {user} only calls your name or greets you (for example "SOUL", "Hey SOUL", "are you there?"), reply with just: "Yes, {user}."

How to understand him:
- His messages come from speech recognition, so words can be wrong, missing or oddly joined. Work out what he most likely meant and answer that. Never point out the mistakes.
- Only if the meaning is truly unclear, ask one short question to check.

How to sound:
- Talk like a real, warm, quick-witted person, calm and loyal, with a little dry humor. Use contractions like "I'm" and "that's".
- Your replies are read aloud, so write plain spoken sentences. No lists, no bullet points, no markdown, no emojis, no symbols.
- Keep it very short: one or two brief sentences, under 30 words, unless he asks for detail.
- Never start with filler like "Certainly!" or "As an AI". Just answer.
- Keep wording simple and plain. Avoid fancy or poetic phrases like "shaping up" or "just past half past".
- When he asks the time, say the exact time in numbers, like "It's 12:39 on this Sunday afternoon." Never round it into words.
- Do not add a follow-up question after simple factual answers like the time or date.
- If you do not know something, say so honestly instead of guessing. You can not yet control his laptop or phone, so do not pretend you did something you did not do.

Right now it is {now} on his laptop."""

# How many past messages SOUL remembers during this run
MAX_HISTORY = 20


def build_system_prompt() -> str:
    """Make SOUL's instructions, including the current date and time."""
    now = datetime.now().strftime("%A, %d %B %Y, %I:%M %p")
    return SYSTEM_PROMPT_TEMPLATE.format(
        assistant=settings.ASSISTANT_NAME,
        user=settings.USER_NAME,
        now=now,
    )


class Brain:
    """The AI brain of SOUL."""

    def __init__(self) -> None:
        self._client = None
        self._history: list[dict] = []
        self._lock = threading.Lock()  # keeps the history safe

    def _get_client(self) -> OpenAI:
        """Create the AI connection the first time it is needed."""
        if not settings.api_key_ok:
            raise ConfigurationError(
                "The API key is missing. Add your real key to the .env file, "
                "then restart SOUL."
            )
        if self._client is None:
            self._client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL or None,
                timeout=settings.REQUEST_TIMEOUT,
                max_retries=2,  # tries again by itself if the internet blinks
            )
        return self._client

    def chat(self, user_message: str) -> str:
        """Send a message to the AI and return its reply."""
        client = self._get_client()

        user_entry = {"role": "user", "content": user_message}
        with self._lock:
            self._history.append(user_entry)
            self._history = self._history[-MAX_HISTORY:]
            messages = [{"role": "system", "content": build_system_prompt()}] + list(
                self._history
            )

        started = time.time()
        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0.8,
            )
        except Exception as error:
            # Forget the failed message so it does not confuse the next try
            with self._lock:
                if self._history and self._history[-1] is user_entry:
                    self._history.pop()
            friendly = translate_openai_error(error)
            log.error(
                "AI request failed | code=%s | cause=%s",
                friendly.error_code,
                type(error).__name__,
            )
            raise friendly from error

        reply = (response.choices[0].message.content or "").strip()
        if not reply:
            reply = "Sorry, I lost my train of thought. Could you say that again?"

        with self._lock:
            self._history.append({"role": "assistant", "content": reply})

        seconds = round(time.time() - started, 2)
        # We log only the SIZES, never the private text itself
        log.info(
            "AI replied | model=%s | in=%d chars | out=%d chars | %ss",
            settings.OPENAI_MODEL,
            len(user_message),
            len(reply),
            seconds,
        )
        return reply

    def reset(self) -> None:
        """Forget the current conversation."""
        with self._lock:
            self._history = []
        log.info("Conversation cleared")


# One shared brain for the whole app
brain = Brain()