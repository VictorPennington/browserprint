"""Debug UI panel for overriding the print command on all incoming jobs."""

import subprocess

import toga
from toga.constants import COLUMN, ROW
from toga.style import Pack

from browserprint.settings import DEBUG_OUTPUT_DIR


class PrintOverridePanel:
    """Checkbox + text input that optionally overrides the printCommand for every job."""

    def __init__(self) -> None:
        self._disable_print_switch = toga.Switch(
            text="Disable printing (download only)",
            style=Pack(padding_right=16),
        )
        self._open_folder_button = toga.Button(
            "Open Download Folder",
            on_press=self._on_open_folder,
            style=Pack(padding_top=4),
        )
        disable_row = toga.Box(
            style=Pack(direction=COLUMN, padding_right=16),
            children=[self._disable_print_switch, self._open_folder_button],
        )
        self._switch = toga.Switch(
            text="Override print command",
            on_change=self._on_switch_change,
        )
        self._input = toga.TextInput(
            placeholder="e.g. ZDesigner GK420d",
            style=Pack(flex=1, padding_left=8),
        )
        self._input.enabled = False
        self.widget = toga.Box(
            style=Pack(direction=ROW, padding_top=8),
            children=[disable_row, self._switch, self._input],
        )

    def _on_open_folder(self, widget) -> None:
        folder = DEBUG_OUTPUT_DIR
        folder.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", str(folder)])

    def _on_switch_change(self, widget) -> None:
        self._input.enabled = self._switch.value

    def is_printing_disabled(self) -> bool:
        """Return True when the 'Disable printing' switch is on."""
        return bool(self._disable_print_switch.value)

    def get_override(self) -> str | None:
        """Return the override command string, or None if override is inactive."""
        if not self._switch.value:
            return None
        value = (self._input.value or "").strip()
        return value if value else None
