from __future__ import annotations

import logging
from pathlib import Path

from pdf_to_epub import diagnostics


def test_configure_logging_writes_and_reuses_rotating_handler(monkeypatch, tmp_path: Path) -> None:
    path = tmp_path / "logs" / "app.log"
    monkeypatch.setattr(diagnostics, "diagnostic_log_path", lambda: path)
    logger = logging.getLogger("pdf_to_epub")
    original_handlers = list(logger.handlers)
    logger.handlers.clear()
    try:
        assert diagnostics.configure_logging() == path
        assert diagnostics.configure_logging() == path
        logging.getLogger("pdf_to_epub.test").info("diagnostic test")
        for handler in logger.handlers:
            handler.flush()
        assert "diagnostic test" in path.read_text(encoding="utf-8")
        assert len(logger.handlers) == 1
    finally:
        for handler in logger.handlers:
            handler.close()
        logger.handlers[:] = original_handlers
