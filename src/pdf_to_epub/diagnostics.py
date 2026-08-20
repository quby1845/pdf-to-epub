"""Persistent diagnostics for conversion failures."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from platformdirs import user_log_path

_LOGGER_NAME = "pdf_to_epub"


def diagnostic_log_path() -> Path:
    """Return the per-user diagnostic log without creating it."""
    return user_log_path("pdf-to-epub-ocr", appauthor=False) / "pdf-to-epub.log"


def configure_logging() -> Path:
    """Configure a bounded UTF-8 log file and return its path."""
    path = diagnostic_log_path()
    logger = logging.getLogger(_LOGGER_NAME)
    if any(getattr(handler, "_pdf_to_epub_handler", False) for handler in logger.handlers):
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler._pdf_to_epub_handler = True  # type: ignore[attr-defined]
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return path
