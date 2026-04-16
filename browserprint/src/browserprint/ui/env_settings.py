"""Environment settings panel — lets the user edit selected .env configurations."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

import toga
from toga.constants import COLUMN, ROW
from toga.style import Pack

from browserprint import settings as _settings

logger = logging.getLogger("browserprint.ui.env_settings")

_ENV_PATH: Path = _settings._DEFAULT_ENV_PATH

_LABEL_WIDTH = 100
_FIELD_WIDTH = 480
_SHORT_FIELD_WIDTH = 120

# Keys managed by this panel (order = display order).
_MANAGED_KEYS = {
    "BROWSERPRINT_LOCAL_API_HOST",
    "BROWSERPRINT_LOCAL_API_PORT",
    "BROWSERPRINT_DEFAULT_API_BASE_URL",
    "BROWSERPRINT_ALLOWED_ORIGINS",
    "BROWSERPRINT_DEBUG_OUTPUT_DIR",
    "BROWSERPRINT_SANCTUM_TIMEOUT_SECONDS",
    "BROWSERPRINT_MANUAL_REQUEST_TIMEOUT_SECONDS",
    "BROWSERPRINT_DOWNLOAD_TIMEOUT_SECONDS",
}


def _read_env_file(path: Path) -> dict[str, str]:
    """Return a dict with all key=value pairs from the .env file (preserving case)."""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            key, _, value = stripped.partition("=")
            result[key.strip()] = value.strip()
    return result


def _write_env_file(path: Path, overrides: dict[str, str]) -> None:
    """Write (or update) .env file, merging *overrides* into any existing content."""
    existing_lines: list[str] = []
    if path.exists():
        existing_lines = path.read_text(encoding="utf-8").splitlines()

    written_keys: set[str] = set()
    output_lines: list[str] = []

    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.partition("=")[0].strip()
            if key in overrides:
                output_lines.append(f"{key}={overrides[key]}")
                written_keys.add(key)
                continue
        output_lines.append(line)

    # Append keys that were not already in the file.
    for key, value in overrides.items():
        if key not in written_keys:
            output_lines.append(f"{key}={value}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(output_lines) + "\n", encoding="utf-8")


class EnvSettingsController:
    """Controller for the environment settings panel."""

    def __init__(self, app: toga.App, on_close: Callable[[], None]) -> None:
        self.app = app
        self.on_close = on_close
        self._status_label: toga.Label | None = None

        # Current env values (read at build time).
        self._env: dict[str, str] = {}

        # Widget references.
        self._host_input: toga.TextInput | None = None
        self._port_input: toga.TextInput | None = None
        self._base_url_input: toga.TextInput | None = None
        self._origins_input: toga.TextInput | None = None
        self._output_dir_input: toga.TextInput | None = None
        self._sanctum_timeout_input: toga.TextInput | None = None
        self._manual_timeout_input: toga.TextInput | None = None
        self._download_timeout_input: toga.TextInput | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_panel(self) -> toga.Box:
        """Build and return the settings panel as an embeddable toga.Box."""
        self._env = _read_env_file(_ENV_PATH)
        panel = toga.Box(style=Pack(direction=COLUMN, padding=12, gap=6))
        self._build_content(panel)
        return panel

    # ------------------------------------------------------------------
    # Internal builders
    # ------------------------------------------------------------------

    def _build_content(self, panel: toga.Box) -> None:
        # ── Server section ─────────────────────────────────────────────
        panel.add(
            toga.Label(
                "Local API Server", style=Pack(font_weight="bold", padding_top=4)
            )
        )
        panel.add(toga.Divider(style=Pack(padding_bottom=4)))

        section_server = toga.Box(style=Pack(direction=COLUMN, padding_left=12, gap=2))
        self._host_input = toga.TextInput(
            value=self._env.get(
                "BROWSERPRINT_LOCAL_API_HOST", _settings.LOCAL_API_HOST
            ),
            placeholder="127.0.0.1",
            style=Pack(width=_FIELD_WIDTH),
        )
        section_server.add(self._field_row("API Host", self._host_input))

        self._port_input = toga.TextInput(
            value=self._env.get(
                "BROWSERPRINT_LOCAL_API_PORT", str(_settings.LOCAL_API_PORT)
            ),
            placeholder="8003",
            style=Pack(width=_SHORT_FIELD_WIDTH),
        )
        section_server.add(self._field_row("API Port", self._port_input))
        panel.add(section_server)

        # ── Laravel backend section ────────────────────────────────────
        panel.add(
            toga.Label(
                "Laravel Backend", style=Pack(font_weight="bold", padding_top=10)
            )
        )
        panel.add(toga.Divider(style=Pack(padding_bottom=4)))

        section_laravel = toga.Box(style=Pack(direction=COLUMN, padding_left=12, gap=2))
        self._base_url_input = toga.TextInput(
            value=self._env.get(
                "BROWSERPRINT_DEFAULT_API_BASE_URL", _settings.DEFAULT_API_BASE_URL
            ),
            placeholder="http://localhost",
            style=Pack(width=_FIELD_WIDTH),
        )
        section_laravel.add(self._field_row("Base URL", self._base_url_input))

        origins_value = self._env.get(
            "BROWSERPRINT_ALLOWED_ORIGINS",
            ",".join(_settings.ALLOWED_ORIGINS),
        )
        self._origins_input = toga.TextInput(
            value=origins_value,
            placeholder="http://localhost,http://127.0.0.1",
            style=Pack(width=_FIELD_WIDTH),
        )
        section_laravel.add(
            self._field_row(
                "Allowed Origins", self._origins_input, hint="Comma-separated"
            )
        )
        panel.add(section_laravel)

        # ── Files section ──────────────────────────────────────────────
        panel.add(toga.Label("Files", style=Pack(font_weight="bold", padding_top=10)))
        panel.add(toga.Divider(style=Pack(padding_bottom=4)))

        section_files = toga.Box(style=Pack(direction=COLUMN, padding_left=12, gap=2))
        self._output_dir_input = toga.TextInput(
            value=self._env.get(
                "BROWSERPRINT_DEBUG_OUTPUT_DIR", str(_settings.DEBUG_OUTPUT_DIR)
            ),
            placeholder=str(Path.home() / "Desktop" / "debug_pdfs"),
            style=Pack(width=500),
        )
        browse_btn = toga.Button(
            "Browse…",
            on_press=self._on_browse_output_dir,
            style=Pack(width=90, margin_left=6),
        )
        dir_row = toga.Box(style=Pack(direction=ROW))
        dir_row.add(self._output_dir_input)
        dir_row.add(browse_btn)
        section_files.add(self._field_row("PDF Output Dir", dir_row))
        panel.add(section_files)

        # ── Timeouts section ───────────────────────────────────────────
        panel.add(
            toga.Label(
                "Timeouts (seconds)", style=Pack(font_weight="bold", padding_top=10)
            )
        )
        panel.add(toga.Divider(style=Pack(padding_bottom=4)))

        section_timeouts = toga.Box(
            style=Pack(direction=COLUMN, padding_left=12, gap=2)
        )
        self._sanctum_timeout_input = toga.TextInput(
            value=self._env.get(
                "BROWSERPRINT_SANCTUM_TIMEOUT_SECONDS",
                str(_settings.SANCTUM_TIMEOUT_SECONDS),
            ),
            placeholder="15",
            style=Pack(width=_SHORT_FIELD_WIDTH),
        )
        section_timeouts.add(
            self._field_row("Sanctum Timeout", self._sanctum_timeout_input)
        )

        self._manual_timeout_input = toga.TextInput(
            value=self._env.get(
                "BROWSERPRINT_MANUAL_REQUEST_TIMEOUT_SECONDS",
                str(_settings.MANUAL_REQUEST_TIMEOUT_SECONDS),
            ),
            placeholder="20",
            style=Pack(width=_SHORT_FIELD_WIDTH),
        )
        section_timeouts.add(
            self._field_row("Manual Request Timeout", self._manual_timeout_input)
        )

        self._download_timeout_input = toga.TextInput(
            value=self._env.get(
                "BROWSERPRINT_DOWNLOAD_TIMEOUT_SECONDS",
                str(_settings.DOWNLOAD_TIMEOUT_SECONDS),
            ),
            placeholder="20",
            style=Pack(width=_SHORT_FIELD_WIDTH),
        )
        section_timeouts.add(
            self._field_row("Download Timeout", self._download_timeout_input)
        )
        panel.add(section_timeouts)

        # ── Save button + status label ─────────────────────────────────
        panel.add(toga.Box(style=Pack(flex=1)))  # spacer

        status_row = toga.Box(style=Pack(direction=ROW, padding_top=10))
        self._status_label = toga.Label(
            "",
            style=Pack(flex=1, color="#2d7a2d"),
        )
        status_row.add(self._status_label)
        status_row.add(
            toga.Button(
                "Save",
                on_press=self._on_save,
                style=Pack(width=80),
            )
        )
        panel.add(status_row)

    def _field_row(
        self, label_text: str, field_widget: toga.Widget, hint: str = ""
    ) -> toga.Box:
        row = toga.Box(style=Pack(direction=ROW, padding_top=1, padding_bottom=1))
        label = label_text if not hint else f"{label_text} ({hint})"
        row.add(toga.Label(label, style=Pack(width=_LABEL_WIDTH, margin_right=6)))
        row.add(field_widget)
        return row

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _resolve_output_dir_initial(self) -> Path:
        if self._output_dir_input.value:
            return Path(self._output_dir_input.value).expanduser()
        return Path.home()

    async def _on_browse_output_dir(self, widget=None) -> None:
        initial = self._resolve_output_dir_initial()
        result = await self.app.main_window.dialog(
            toga.SelectFolderDialog(
                "Select PDF Output Directory", initial_directory=initial
            )
        )
        if result is not None:
            self._output_dir_input.value = str(result)

    def _on_save(self, widget=None) -> None:
        overrides: dict[str, str] = {
            "BROWSERPRINT_LOCAL_API_HOST": self._host_input.value.strip(),
            "BROWSERPRINT_LOCAL_API_PORT": self._port_input.value.strip(),
            "BROWSERPRINT_DEFAULT_API_BASE_URL": self._base_url_input.value.strip(),
            "BROWSERPRINT_ALLOWED_ORIGINS": self._origins_input.value.strip(),
            "BROWSERPRINT_DEBUG_OUTPUT_DIR": self._output_dir_input.value.strip(),
            "BROWSERPRINT_SANCTUM_TIMEOUT_SECONDS": self._sanctum_timeout_input.value.strip(),
            "BROWSERPRINT_MANUAL_REQUEST_TIMEOUT_SECONDS": self._manual_timeout_input.value.strip(),
            "BROWSERPRINT_DOWNLOAD_TIMEOUT_SECONDS": self._download_timeout_input.value.strip(),
        }
        # Remove blank values to avoid overwriting with empty strings.
        overrides = {k: v for k, v in overrides.items() if v}

        try:
            _write_env_file(_ENV_PATH, overrides)
            logger.info("Settings saved to %s", _ENV_PATH)
            if self._status_label:
                self._status_label.text = (
                    "Settings saved. Restart the app to apply changes."
                )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to save settings: %s", exc)
            if self._status_label:
                self._status_label.text = f"Error saving settings: {exc}"
