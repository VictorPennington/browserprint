"""Logging utilities for piping Python logs into Toga widgets."""

import logging
from collections.abc import Callable


class _TogaTextLogHandler(logging.Handler):
    """Forward Python log records to a UI callback."""

    def __init__(self, emit_to_ui: Callable[[str], None]) -> None:
        super().__init__()
        self.emit_to_ui = emit_to_ui

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        try:
            self.emit_to_ui(message)
        except Exception:
            return


def install_app_log_handler(emit_to_ui: Callable[[str], None]) -> None:
    """Attach a log handler that mirrors package logs into a UI callback."""
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Handler for UI
    ui_handler = _TogaTextLogHandler(emit_to_ui)
    ui_handler.setFormatter(formatter)

    # Handler for STDOUT
    stdout_handler = logging.StreamHandler()
    stdout_handler.setFormatter(formatter)

    logger = logging.getLogger("browserprint")
    logger.setLevel(logging.INFO)
    logger.addHandler(ui_handler)
    logger.addHandler(stdout_handler)
