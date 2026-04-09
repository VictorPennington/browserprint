"""
Manage requests from browser to printer without dialog boxes
"""

import logging
import threading

import toga
from toga.constants import COLUMN
from toga.style import Pack

from browserprint.api.server import run_local_server


class _TogaTextLogHandler(logging.Handler):
    """Forward Python log records to the app's on-screen log panel."""

    def __init__(self, app: "BrowserPrint") -> None:
        super().__init__()
        self.app = app

    def emit(self, record: logging.LogRecord) -> None:
        message = self.format(record)
        try:
            self.app.loop.call_soon_threadsafe(self.app.append_log_line, message)
        except Exception:
            return


class BrowserPrint(toga.App):
    _MAX_LOG_LINES = 400

    def startup(self):
        """Construct and show the Toga application.

        Usually, you would add your application to a main content box.
        We then create a main window (with a name matching the app), and
        show the main window.
        """
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10, flex=1))
        main_box.add(toga.Label("Application logs", style=Pack(padding_bottom=6)))

        self.log_output = toga.MultilineTextInput(
            readonly=True,
            style=Pack(flex=1),
        )
        main_box.add(self.log_output)

        self._install_log_handler()
        self.append_log_line("Starting BrowserPrint...")

        # Run the local API server without blocking the UI event loop.
        self.api_thread = threading.Thread(
            target=run_local_server,
            kwargs={"host": "127.0.0.1", "port": 8003},
            daemon=True,
            name="browserprint-local-api",
        )
        self.api_thread.start()

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()

    def append_log_line(self, line: str) -> None:
        existing = self.log_output.value or ""
        lines = existing.splitlines() if existing else []
        lines.append(line)
        self.log_output.value = "\n".join(lines[-self._MAX_LOG_LINES :])

    def _install_log_handler(self) -> None:
        handler = _TogaTextLogHandler(self)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%H:%M:%S",
            )
        )

        logger = logging.getLogger("browserprint")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)


def main():
    return BrowserPrint()
