"""
logging_config.py
-----------------
SOUL's diary. It writes messages to the screen AND to a file (logs/soul.log).
Other files use it like this:

    from backend.logging_config import get_logger
    log = get_logger("brain")
    log.info("Something happened")
    log.error("Something went wrong")
"""

import logging
from logging.handlers import RotatingFileHandler

from backend.config import settings

_already_set_up = False


def setup_logging() -> None:
    """Prepare the diary. It only runs once, even if called many times."""
    global _already_set_up
    if _already_set_up:
        return

    # Make the "logs" folder if it does not exist yet
    settings.LOGS_DIR.mkdir(exist_ok=True)

    # How each line looks: time | level | who wrote it | message
    line_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )

    soul_logger = logging.getLogger("soul")
    soul_logger.setLevel(settings.LOG_LEVEL)
    soul_logger.propagate = False  # stops lines being printed twice

    # 1) Show messages on the screen (terminal)
    screen = logging.StreamHandler()
    screen.setFormatter(line_format)
    soul_logger.addHandler(screen)

    # 2) Save messages in a file.
    #    When the file reaches about 1 MB, a new one starts.
    #    We keep 3 old files, so the diary never fills your disk.
    file_handler = RotatingFileHandler(
        settings.LOGS_DIR / "soul.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(line_format)
    soul_logger.addHandler(file_handler)

    _already_set_up = True


def get_logger(name: str) -> logging.Logger:
    """Get a diary pen with a name, like get_logger('brain')."""
    setup_logging()
    return logging.getLogger(f"soul.{name}")