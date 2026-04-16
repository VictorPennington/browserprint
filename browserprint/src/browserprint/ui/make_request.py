"""Manual request testing window for authenticated endpoint calls."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import toga
from toga.constants import COLUMN, ROW
from toga.style import Pack

from browserprint.api.manual_request_client import (
    ManualRequestClient,
    ManualRequestClientError,
    ManualRequestResult,
)
from browserprint.auth_config import AuthConfigStore
from browserprint.auth_utils import wrap_status_message

logger = logging.getLogger("browserprint.ui.make_request")


class MakeRequestController:
    """Manage a manual request UI backed by persisted auth configuration."""

    def __init__(
        self,
        app: toga.App,
        log_line: Callable[[str], None],
        auth_store: AuthConfigStore | None = None,
        request_client: ManualRequestClient | None = None,
    ) -> None:
        self.app = app
        self.log_line = log_line
        self.auth_store = auth_store or AuthConfigStore()
        self.request_client = request_client or ManualRequestClient()
        self.auth_config = self.auth_store.load()
        self.request_window = None

    def build_panel(self) -> toga.Box:
        """Build and return the panel as a toga.Box for embedding."""
        content = toga.Box(style=Pack(direction=COLUMN, padding=12, gap=8))
        self._build_content(content)
        self._refresh_values()
        return content

    def open(self, widget=None) -> None:
        self.auth_config = self.auth_store.load()

        if self.request_window is None:
            self._build_window()

        self._refresh_values()
        self.request_window.show()

    def _build_window(self) -> None:
        content = toga.Box(style=Pack(direction=COLUMN, padding=12, gap=8))
        self._build_content(content)

        self.request_window = toga.Window(title="Make Request")
        self.request_window.content = content

    def _build_content(self, content: toga.Box) -> None:

        content.add(toga.Label("Saved API Base URL"))
        self.base_url_value = toga.Label("", style=Pack(padding_bottom=4))
        content.add(self.base_url_value)

        content.add(toga.Label("Endpoint Path (or full URL)"))
        self.endpoint_input = toga.TextInput(
            value="/api/browserprint/ping",
            placeholder="/api/example/path",
            style=Pack(flex=1),
        )
        content.add(self.endpoint_input)

        content.add(toga.Label("HTTP Method"))
        self.method_input = toga.TextInput(
            value="POST",
            placeholder="GET, POST, PUT, PATCH, DELETE",
            style=Pack(width=220),
        )
        content.add(self.method_input)

        content.add(toga.Label("JSON Payload (optional)"))
        self.payload_input = toga.MultilineTextInput(
            value="{}",
            style=Pack(height=120, flex=0),
        )
        content.add(self.payload_input)

        button_row = toga.Box(style=Pack(direction=ROW, margin_top=8, gap=8))
        self.send_button = toga.Button("Send", on_press=self._send_request)
        button_row.add(self.send_button)
        content.add(button_row)

        self.request_status_output = toga.MultilineTextInput(
            readonly=True,
            value="Ready to send a request.",
            style=Pack(margin_top=6, height=120, flex=0),
        )
        content.add(self.request_status_output)

    def _refresh_values(self) -> None:
        self.base_url_value.text = self.auth_config.api_base_url
        self._set_status(
            "Loaded auth settings. "
            f"Token present={self.auth_config.token_present}, storage={self.auth_config.token_storage}."
        )

    def _send_request(self, widget=None) -> None:
        self.auth_config = self.auth_store.load()
        token = self.auth_store.get_token()
        if not token:
            self._set_status("No token available. Generate token first.")
            self.log_line("Make Request aborted: no stored token.")
            return

        endpoint_path = (self.endpoint_input.value or "").strip()
        if not endpoint_path:
            self._set_status("Endpoint path is required.")
            self.log_line("Make Request aborted: endpoint path is empty.")
            return

        method = (self.method_input.value or "POST").strip().upper() or "POST"
        payload_text = self.payload_input.value or ""

        self._set_send_enabled(False)
        self._set_status("Sending request...")

        threading.Thread(
            target=self._send_request_worker,
            args=(method, endpoint_path, payload_text, token),
            daemon=True,
            name="browserprint-make-request",
        ).start()

    def _send_request_worker(
        self,
        method: str,
        endpoint_path: str,
        payload_text: str,
        token: str,
    ) -> None:
        try:
            result = self.request_client.send(
                base_url=self.auth_config.api_base_url,
                token=token,
                endpoint_path=endpoint_path,
                method=method,
                payload_text=payload_text,
            )
            self.app.loop.call_soon_threadsafe(self._on_send_success, result)
        except ManualRequestClientError as exc:
            self.app.loop.call_soon_threadsafe(self._on_send_error, str(exc))
        except Exception:
            logger.exception("Unexpected manual request failure")
            self.app.loop.call_soon_threadsafe(
                self._on_send_error,
                "Manual request failed due to unexpected error",
            )

    def _on_send_success(self, result: ManualRequestResult) -> None:
        if result.ok:
            self._set_status(
                f"Request succeeded with status {result.status_code}.\n\n{result.body_preview}"
            )
        else:
            self._set_status(
                f"Request failed with status {result.status_code}.\n\n{result.body_preview}"
            )
        self._set_send_enabled(True)
        self.log_line(
            f"Manual request {result.method} {result.url} -> {result.status_code}"
        )

    def _on_send_error(self, message: str) -> None:
        self._set_status(f"Request failed: {message}")
        self._set_send_enabled(True)
        self.log_line(f"Manual request failed: {message}")

    def _set_send_enabled(self, enabled: bool) -> None:
        self.send_button.enabled = enabled

    def _set_status(self, message: str) -> None:
        self.request_status_output.value = wrap_status_message(message)
