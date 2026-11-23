"""
config.py
---------
This file reads your settings from the .env file and checks them.
Every other file in SOUL gets its settings from here.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# The main SOUL folder (one level above "backend")
BASE_DIR = Path(__file__).resolve().parent.parent

# Read the .env file
load_dotenv(BASE_DIR / ".env", override=True)

VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
PLACEHOLDER_KEYS = {"", "paste-your-key-here", "your-key-goes-here"}


def _read_number(name: str, default: int) -> int:
    """Read a number from .env. If it is wrong, use the default."""
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default


class Settings:
    """All of SOUL's settings in one place."""

    def __init__(self) -> None:
        # Folders
        self.BASE_DIR: Path = BASE_DIR
        self.FRONTEND_DIR: Path = BASE_DIR / "frontend"
        self.LOGS_DIR: Path = BASE_DIR / "logs"

        # Secret key and model (from .env)
        self.OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
        self.OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        # The web address of the AI service (Gemini's OpenAI-compatible address).
        # If this is empty, the OpenAI SDK uses its normal default address.
        self.OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "").strip()
        self.ASSISTANT_NAME: str = os.getenv("ASSISTANT_NAME", "SOUL").strip() or "SOUL"
        self.USER_NAME: str = os.getenv("USER_NAME", "Bargav").strip() or "Bargav"

        # Logging level (how much detail goes in the log file)
        level = os.getenv("LOG_LEVEL", "INFO").strip().upper()
        self.LOG_LEVEL: str = level if level in VALID_LOG_LEVELS else "INFO"

        # How many seconds to wait for the AI before giving up
        self.REQUEST_TIMEOUT: int = _read_number("REQUEST_TIMEOUT", 30)

    @property
    def api_key_ok(self) -> bool:
        """True only if a real API key was added to .env."""
        return self.OPENAI_API_KEY not in PLACEHOLDER_KEYS

    def problems(self) -> list[str]:
        """A list of things that are wrong with the settings (empty = all good)."""
        found = []
        if not self.api_key_ok:
            found.append("OPENAI_API_KEY is missing. Add your real key to the .env file.")
        if not self.FRONTEND_DIR.exists():
            found.append("The 'frontend' folder was not found.")
        return found


# One shared settings object for the whole app
settings = Settings()