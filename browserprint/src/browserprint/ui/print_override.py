"""Debug UI panel for overriding the print command on all incoming jobs."""

import toga
from toga.constants import ROW
from toga.style import Pack


class PrintOverridePanel:
    """Checkbox + text input that optionally overrides the printCommand for every job."""

    def __init__(self) -> None:
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
            children=[self._switch, self._input],
        )

    def _on_switch_change(self, widget) -> None:
        self._input.enabled = self._switch.value

    def get_override(self) -> str | None:
        """Return the override command string, or None if override is inactive."""
        if not self._switch.value:
            return None
        value = (self._input.value or "").strip()
        return value if value else None
