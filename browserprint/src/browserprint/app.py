"""
Manage requests from browser to printer without dialog boxes
"""

import threading

import toga
from toga.constants import COLUMN
from toga.style import Pack

from browserprint.api.server import run_local_server
from browserprint.settings import LOCAL_API_HOST, LOCAL_API_PORT
from browserprint.ui.auth_settings import AuthSettingsController
from browserprint.ui.download_pdf import DownloadPdfController
from browserprint.ui.log_panel import LogPanel
from browserprint.ui.logging import install_app_log_handler
from browserprint.ui.make_request import MakeRequestController


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

        self.auth_controller = AuthSettingsController(
            app=self,
            log_line=self.log_panel.append_line,
        )
        self.make_request_controller = MakeRequestController(
            app=self,
            log_line=self.log_panel.append_line,
        )
        self.download_pdf_controller = DownloadPdfController(
            app=self,
            log_line=self.log_panel.append_line,
        )

        install_app_log_handler(self._emit_log_line)
        self.log_panel.append_line("Starting BrowserPrint...")

        self._install_toolbar_commands()
        self.log_panel.append_line(self.auth_controller.describe_token_state())

        # Run the local API server without blocking the UI event loop.
        self.api_thread = threading.Thread(
            target=run_local_server,
            kwargs={"host": LOCAL_API_HOST, "port": LOCAL_API_PORT},
            daemon=True,
            name="browserprint-local-api",
        )
        self.api_thread.start()

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = main_box
        self.main_window.show()

    def _install_toolbar_commands(self) -> None:
        self.commands.add(
            toga.Command(
                self._open_auth_settings,
                text="Generate Bearer Token",
                tooltip="Configure eDiary auth settings and token actions",
            )
        )
        self.commands.add(
            toga.Command(
                self._open_make_request,
                text="Make Request",
                tooltip="Send custom authenticated requests for endpoint testing",
            )
        )
        self.commands.add(
            toga.Command(
                self._open_download_pdf,
                text="Download PDF",
                tooltip="Download a PDF from an authenticated endpoint",
            )
        )

    def _open_auth_settings(self, widget=None) -> None:
        self.auth_controller.open(widget)

    def _open_make_request(self, widget=None) -> None:
        self.make_request_controller.open(widget)

    def _open_download_pdf(self, widget=None) -> None:
        self.download_pdf_controller.open(widget)

    def _emit_log_line(self, line: str) -> None:
        self.loop.call_soon_threadsafe(self.log_panel.append_line, line)


def main():
    return BrowserPrint()
