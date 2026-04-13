"""UI log panel widget and line buffering behavior."""

import toga
from toga.style import Pack


class LogPanel:
    """Owns the multiline log widget and appends lines with a size cap."""

    def __init__(self, max_lines: int = 400) -> None:
        self._max_lines = max_lines
        self.widget = toga.MultilineTextInput(
            readonly=True,
            style=Pack(height=240),
        )

    def append_line(self, line: str) -> None:
        existing = self.widget.value or ""
        lines = existing.splitlines() if existing else []
        lines.insert(0, line)
        self.widget.value = "\n".join(lines[: self._max_lines])
