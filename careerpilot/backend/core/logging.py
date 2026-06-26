"""Centralized logging setup (Module 18 — activity.log + console).

CSV artifact logging (emails_sent.csv, etc.) is layered on top of this in the
relevant feature modules; here we configure the root application logger.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from careerpilot.backend.config.settings import get_settings

_CONFIGURED = False


def configure_logging() -> None:
    """Configure console + rotating-file handlers once per process."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    settings = get_settings()
    level = getattr(logging, settings.logging.level.upper(), logging.INFO)

    root = logging.getLogger("careerpilot")
    root.setLevel(level)
    root.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    log_dir = Path(settings.logging.directory)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "activity.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except OSError:
        # Filesystem may be read-only in some deploy targets; console still works.
        root.warning("Could not create log directory %s; file logging disabled", log_dir)

    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced child of the application logger."""
    configure_logging()
    return logging.getLogger(f"careerpilot.{name}")
