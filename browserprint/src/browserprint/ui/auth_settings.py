"""Auth settings window and Sanctum token lifecycle handlers."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import toga
from toga.constants import BOLD, COLUMN, ROW
from toga.style import Pack

from browserprint.api.sanctum_client import SanctumClient, SanctumClientError
from browserprint.auth_config import AuthConfig, AuthConfigStore
from browserprint.auth_utils import validate_base_url, wrap_status_message
from browserprint.settings import DEFAULT_API_BASE_URL

logger = logging.getLogger("browserprint.ui.auth_settings")


class AuthSettingsController:
    """Manage authentication settings UI and token operations."""

    def __init__(self, app: toga.App, log_line: Callable[[str], None]) -> None:
        self.app = app
        self.log_line = log_line
        self.auth_store = AuthConfigStore()
        self.auth_config = self.auth_store.load()
        self.sanctum_client = SanctumClient()
        self.auth_window = None

    def describe_token_state(self) -> str:
        return (
            "Auth config loaded (token present: "
            f"{self.auth_config.token_present}, storage: {self.auth_config.token_storage})."
        )

    def build_panel(self) -> toga.Box:
        """Build and return the settings panel as a toga.Box for embedding."""
        content = toga.Box(style=Pack(direction=COLUMN, margin=12, gap=4))
        self._build_content(content)
        self._refresh_values()
        return content

    def open(self, widget=None) -> None:
        self.auth_config = self.auth_store.load()

        if self.auth_window is None:
            self._build_window()

        self._refresh_values()
        self.auth_window.show()

    def _build_window(self) -> None:
        content = toga.Box(style=Pack(direction=COLUMN, margin=12, gap=4))
        self._build_content(content)

        self.auth_window = toga.Window(title="eDiary Authentication")
        self.auth_window.content = content

    def _build_content(self, content: toga.Box) -> None:
        _LABEL_WIDTH = 120
        _FIELD_WIDTH = 600

        self.api_base_url_input = toga.TextInput(
            value=self.auth_config.api_base_url,
            placeholder=DEFAULT_API_BASE_URL,
            style=Pack(width=_FIELD_WIDTH),
        )
        self.email_input = toga.TextInput(
            value=self.auth_config.email,
            placeholder="user@example.com",
            style=Pack(width=_FIELD_WIDTH),
        )
        self.password_input = toga.PasswordInput(
            placeholder="Password (not persisted)",
            style=Pack(width=_FIELD_WIDTH),
        )
        self.device_name_input = toga.TextInput(
            value=self.auth_config.device_name,
            placeholder="browserprint",
            style=Pack(width=_FIELD_WIDTH),
        )
        self.replace_existing_switch = toga.Switch(
            text="Replace existing token",
            value=self.auth_config.replace_existing,
            style=Pack(margin_top=4),
        )

        def _row(label_text: str, field: toga.Widget) -> toga.Box:
            row = toga.Box(style=Pack(direction=ROW, gap=8, margin_bottom=2))
            row.add(toga.Label(label_text, style=Pack(width=_LABEL_WIDTH)))
            row.add(field)
            return row

        content.add(_row("API Base URL", self.api_base_url_input))
        content.add(_row("Email", self.email_input))
        content.add(_row("Password", self.password_input))
        content.add(_row("Device Name", self.device_name_input))
        content.add(self.replace_existing_switch)

        self.auth_status_output = toga.MultilineTextInput(
            readonly=True,
            value="Token state: unknown",
            style=Pack(margin_top=6, height=50, flex=0),
        )
        content.add(self.auth_status_output)

        button_row = toga.Box(style=Pack(direction=ROW, margin_top=8, gap=8, flex=1))
        button_row.add(toga.Box(style=Pack(flex=1)))  # spacer
        self.save_settings_button = toga.Button(
            "Save Settings",
            on_press=self._save_auth_settings,
            style=Pack(font_weight=BOLD),
        )
        self.generate_token_button = toga.Button(
            "Generate Token",
            on_press=self._generate_token,
            style=Pack(font_weight=BOLD),
        )
        self.test_session_button = toga.Button(
            "Test Session", on_press=self._test_session, style=Pack(font_weight=BOLD)
        )
        self.revoke_token_button = toga.Button(
            "Revoke Token", on_press=self._revoke_token, style=Pack(font_weight=BOLD)
        )
        button_row.add(self.save_settings_button)
        button_row.add(self.generate_token_button)
        button_row.add(self.test_session_button)
        button_row.add(self.revoke_token_button)
        content.add(button_row)

    def _refresh_values(self) -> None:
        self.api_base_url_input.value = self.auth_config.api_base_url
        self.email_input.value = self.auth_config.email
        self.device_name_input.value = self.auth_config.device_name
        self.replace_existing_switch.value = self.auth_config.replace_existing
        self.password_input.value = ""

        self._set_status(
            "Token state: "
            f"present={self.auth_config.token_present}, storage={self.auth_config.token_storage}"
        )

    def _save_auth_settings(self, widget=None) -> bool:
        current = self.auth_store.load()

        base_url_candidate = (
            self.api_base_url_input.value or ""
        ).strip() or DEFAULT_API_BASE_URL
        try:
            base_url = validate_base_url(base_url_candidate)
        except ValueError as exc:
            self._set_status(str(exc))
            self.log_line(str(exc))
            return False

        config = AuthConfig(
            api_base_url=base_url,
            email=(self.email_input.value or "").strip(),
            device_name=(self.device_name_input.value or "").strip() or "browserprint",
            replace_existing=bool(self.replace_existing_switch.value),
            token_present=current.token_present,
            token_last_updated=current.token_last_updated,
            token_storage=current.token_storage,
            token_value=current.token_value,
        )
        self.auth_store.save(config)
        self.auth_config = config
        self._set_status(
            "Token state: "
            f"present={config.token_present}, storage={config.token_storage}"
        )
        self.log_line("Auth settings saved.")
        return True

    def _set_auth_actions_enabled(self, enabled: bool) -> None:
        self.save_settings_button.enabled = enabled
        self.generate_token_button.enabled = enabled
        self.test_session_button.enabled = enabled
        self.revoke_token_button.enabled = enabled

    def _generate_token(self, widget) -> None:
        if not self._save_auth_settings(widget):
            return

        password = (self.password_input.value or "").strip()
        if not self.auth_config.email:
            self._set_status("Missing email.")
            self.log_line("Generate token aborted: email is required.")
            return
        if not password:
            self._set_status("Missing password.")
            self.log_line("Generate token aborted: password is required.")
            return

        self._set_auth_actions_enabled(False)
        self._set_status("Generating token...")

        threading.Thread(
            target=self._generate_token_worker,
            args=(password,),
            daemon=True,
            name="browserprint-generate-token",
        ).start()

    def _generate_token_worker(self, password: str) -> None:
        try:
            token = self.sanctum_client.generate_token(
                base_url=self.auth_config.api_base_url,
                email=self.auth_config.email,
                password=password,
                device_name=self.auth_config.device_name,
                replace_existing=self.auth_config.replace_existing,
            )
            self.auth_store.set_token(token)
            self.auth_config = self.auth_store.load()

            masked = self._mask_token(token)
            self.app.loop.call_soon_threadsafe(self._on_generate_token_success, masked)
        except SanctumClientError as exc:
            self.app.loop.call_soon_threadsafe(
                self._on_auth_action_error,
                f"Token generation failed: {exc}",
            )
        except Exception:
            logger.exception("Unexpected token generation failure")
            self.app.loop.call_soon_threadsafe(
                self._on_auth_action_error,
                "Token generation failed due to unexpected error",
            )

    def _on_generate_token_success(self, masked_token: str) -> None:
        self.password_input.value = ""
        self._refresh_values()
        self._set_status("Token generated successfully.")
        self._set_auth_actions_enabled(True)
        self.log_line(f"Token generated successfully: {masked_token}")

    def _test_session(self, widget) -> None:
        if not self._save_auth_settings(widget):
            return

        token = self.auth_store.get_token()
        if not token:
            self._set_status("No token available. Generate token first.")
            self.log_line("Test session aborted: no stored token.")
            return

        self._set_auth_actions_enabled(False)
        self._set_status("Testing session...")

        threading.Thread(
            target=self._test_session_worker,
            args=(token,),
            daemon=True,
            name="browserprint-test-session",
        ).start()

    def _test_session_worker(self, token: str) -> None:
        try:
            result = self.sanctum_client.ping(
                base_url=self.auth_config.api_base_url,
                token=token,
            )
            self.app.loop.call_soon_threadsafe(
                self._on_test_session_result,
                result.ok,
                result.status_code,
                result.message,
            )
        except SanctumClientError as exc:
            self.app.loop.call_soon_threadsafe(
                self._on_auth_action_error,
                f"Session test failed: {exc}",
            )
        except Exception:
            logger.exception("Unexpected session test failure")
            self.app.loop.call_soon_threadsafe(
                self._on_auth_action_error,
                "Session test failed due to unexpected error",
            )

    def _on_test_session_result(self, ok: bool, status_code: int, message: str) -> None:
        self.password_input.value = ""
        if ok:
            self._set_status("Session is valid.")
            self.log_line(f"Session test succeeded (status {status_code}): {message}")
        else:
            self._set_status("Session test failed.")
            self.log_line(f"Session test failed (status {status_code}): {message}")
        self._set_auth_actions_enabled(True)

    def _revoke_token(self, widget) -> None:
        if not self._save_auth_settings(widget):
            return

        token = self.auth_store.get_token()
        if not token:
            self._set_status("No token available to revoke.")
            self.log_line("Revoke token aborted: no stored token.")
            return

        self._set_auth_actions_enabled(False)
        self._set_status("Revoking token...")

        threading.Thread(
            target=self._revoke_token_worker,
            args=(token,),
            daemon=True,
            name="browserprint-revoke-token",
        ).start()

    def _revoke_token_worker(self, token: str) -> None:
        try:
            self.sanctum_client.revoke_token(
                base_url=self.auth_config.api_base_url,
                token=token,
            )
            self.auth_store.clear_token()
            self.auth_config = self.auth_store.load()
            self.app.loop.call_soon_threadsafe(self._on_revoke_token_success)
        except SanctumClientError as exc:
            self.app.loop.call_soon_threadsafe(
                self._on_auth_action_error,
                f"Token revoke failed: {exc}",
            )
        except Exception:
            logger.exception("Unexpected token revoke failure")
            self.app.loop.call_soon_threadsafe(
                self._on_auth_action_error,
                "Token revoke failed due to unexpected error",
            )

    def _on_revoke_token_success(self) -> None:
        self.password_input.value = ""
        self._refresh_values()
        self._set_status("Token revoked successfully.")
        self._set_auth_actions_enabled(True)
        self.log_line("Token revoked successfully.")

    def _on_auth_action_error(self, message: str) -> None:
        self.password_input.value = ""
        self._set_status(message)
        self._set_auth_actions_enabled(True)
        self.log_line(message)

    def _set_status(self, message: str) -> None:
        self.auth_status_output.value = wrap_status_message(message)

    @staticmethod
    def _mask_token(token: str) -> str:
        if len(token) <= 8:
            return "****"
        return f"{token[:4]}...{token[-4:]}"
