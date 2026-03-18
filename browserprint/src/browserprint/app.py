"""
Manage requests from browser to printer without dialog boxes
"""

import threading

import toga

from browserprint.api.server import run_local_server


class BrowserPrint(toga.App):
    def startup(self):
        """Construct and show the Toga application.

        Usually, you would add your application to a main content box.
        We then create a main window (with a name matching the app), and
        show the main window.
        """
        main_box = toga.Box()

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


def main():
    return BrowserPrint()
