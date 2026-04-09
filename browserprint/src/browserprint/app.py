"""
Manage requests from browser to printer without dialog boxes
"""

import threading

import toga
from toga.constants import COLUMN
from toga.style import Pack

from browserprint.api.server import run_local_server
from browserprint.ui.log_panel import LogPanel
from browserprint.ui.logging import install_app_log_handler


class BrowserPrint(toga.App):
    def startup(self):
        """Construct and show the Toga application.

        Usually, you would add your application to a main content box.
        We then create a main window (with a name matching the app), and
        show the main window.
        """
        main_box = toga.Box(style=Pack(direction=COLUMN, padding=10, flex=1))
        main_box.add(toga.Label("Application logs", style=Pack(padding_bottom=6)))

        self.log_panel = LogPanel()
        main_box.add(self.log_panel.widget)

        install_app_log_handler(self._emit_log_line)
        self.log_panel.append_line("Starting BrowserPrint...")

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

    def _emit_log_line(self, line: str) -> None:
        self.loop.call_soon_threadsafe(self.log_panel.append_line, line)


def main():
    return BrowserPrint()
