"""
Manage requests from browser to printer without dialog boxes
"""

import threading

import toga
from toga.constants import COLUMN, ROW
from toga.style import Pack

from browserprint.api.server import run_local_server
from browserprint.settings import LOCAL_API_HOST, LOCAL_API_PORT, START_MINIMIZED
from browserprint.ui.auth_settings import AuthSettingsController
from browserprint.ui.download_pdf import DownloadPdfController
from browserprint.ui.env_settings import EnvSettingsController
from browserprint.ui.log_panel import LogPanel
from browserprint.ui.logging import install_app_log_handler
from browserprint.ui.make_request import MakeRequestController
from browserprint.ui.print_override import PrintOverridePanel


class BrowserPrint(toga.App):
    def startup(self):
        """Construct and show the Toga application.

        Usually, you would add your application to a main content box.
        We then create a main window (with a name matching the app), and
        show the main window.
        """
        main_box = toga.Box(style=Pack(direction=COLUMN, margin=10, flex=1))

        # Header row with "Application logs" label and "Clear Logs" button
        header_box = toga.Box(
            style=Pack(direction=ROW, align_items="center", margin_bottom=6)
        )
        header_box.add(toga.Label("Application logs", style=Pack(flex=1)))
        clear_button = toga.Button(
            "Clear Logs",
            on_press=self._on_clear_logs,
        )
        header_box.add(clear_button)
        main_box.add(header_box)

        self.log_panel = LogPanel()
        main_box.add(self.log_panel.widget)

        self.print_override_panel = PrintOverridePanel()
        main_box.add(self.print_override_panel.widget)

        from browserprint.api import routes as _routes
        from browserprint.api.downloads import service as _download_service

        _routes.set_print_override_provider(self.print_override_panel.get_override)
        _download_service.set_printing_disabled_provider(
            self.print_override_panel.is_printing_disabled
        )

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

        def _scrollable_panel(panel: toga.Widget) -> toga.ScrollContainer:
            return toga.ScrollContainer(
                content=panel,
                horizontal=False,
                vertical=True,
                style=Pack(flex=1),
            )

        self.env_settings_controller = EnvSettingsController(
            app=self,
            on_close=self._show_main_tab,
        )

        self._commands_container = toga.OptionContainer(
            content=[
                toga.OptionItem(
                    "Token Config",
                    _scrollable_panel(self.auth_controller.build_panel()),
                ),
                toga.OptionItem(
                    "Make Request",
                    _scrollable_panel(self.make_request_controller.build_panel()),
                ),
                toga.OptionItem(
                    "Download PDF",
                    _scrollable_panel(self.download_pdf_controller.build_panel()),
                ),
                toga.OptionItem(
                    "Settings",
                    _scrollable_panel(self.env_settings_controller.build_panel()),
                ),
            ],
            style=Pack(flex=1),
        )
        main_box.add(self._commands_container)

        self._main_content = main_box

        install_app_log_handler(self._emit_log_line)
        self.log_panel.append_line("Starting BrowserPrint...")

        self.log_panel.append_line(self.auth_controller.describe_token_state())

        # Run the local API server without blocking the UI event loop.
        self.api_thread = threading.Thread(
            target=run_local_server,
            kwargs={"host": LOCAL_API_HOST, "port": LOCAL_API_PORT},
            daemon=True,
            name="browserprint-local-api",
        )
        self.api_thread.start()

        self.main_window = toga.MainWindow(
            title=self.formal_name, size=(800, 600), position=(0, 0)
        )
        self.main_window.content = self._main_content
        self.main_window.on_close = self._on_main_window_close

        self._setup_tray()

        if START_MINIMIZED:
            self.main_window.hide()
        else:
            self.main_window.show()

    def _setup_tray(self) -> None:
        """Create a system-tray icon; clicking it toggles the main window."""
        self._tray_icon = toga.SimpleStatusIcon(
            text=self.formal_name,
            on_press=self._on_tray_press,
        )
        self.status_icons.add(self._tray_icon)

    def _on_tray_press(self, widget=None, **kwargs) -> None:
        if self.main_window.visible:
            self.main_window.hide()
        else:
            self.main_window.show()

    def _on_main_window_close(self, window, **kwargs) -> bool:
        """Minimize to tray instead of exiting when the window is closed."""
        self.main_window.hide()
        return False

    def _show_main_tab(self) -> None:
        self._commands_container.current_tab = self._commands_container.content[0]

    def _emit_log_line(self, line: str) -> None:
        self.loop.call_soon_threadsafe(self.log_panel.append_line, line)

    def _on_clear_logs(self, widget: toga.Button = None, **kwargs) -> None:
        """Clear all logs from the log panel."""
        self.log_panel.clear_logs()


def main():
    return BrowserPrint()
