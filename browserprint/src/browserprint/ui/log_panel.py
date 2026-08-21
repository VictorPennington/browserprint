"""UI log panel widget and line buffering behavior."""

import toga
from toga.style import Pack

_SEPARATOR = "-" * 55


class LogPanel:
    """Owns the log multiline text widget and prepends new entries."""

    def __init__(self, max_lines: int = 400) -> None:
        self._max_lines = max_lines
        self._lines: list[str] = []
        self.widget = toga.MultilineTextInput(
            readonly=True,
            style=Pack(flex=1),
        )

    def append_line(self, line: str) -> None:
        entry = f"{line}\n{_SEPARATOR}"
        self._lines.insert(0, entry)
        if len(self._lines) > self._max_lines:
            self._lines = self._lines[: self._max_lines]
        self.widget.value = "\n".join(self._lines)
        self.widget.scroll_to_top()

    def clear_logs(self) -> None:
        """Clear all log entries from the panel."""
        self._lines.clear()
        self.widget.value = ""
