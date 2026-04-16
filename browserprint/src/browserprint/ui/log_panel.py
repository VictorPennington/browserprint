"""UI log panel widget and line buffering behavior."""

import toga
from toga.style import Pack


class LogPanel:
    """Owns the log table widget and appends lines with a size cap.

    Uses headings=None with an explicit accessor to suppress the column header.
    Rows are prepended via insert(0) so the full list is never rebuilt.
    """

    def __init__(self, max_lines: int = 400) -> None:
        self._max_lines = max_lines
        self.widget = toga.Table(
            headings=None,
            accessors=["log"],
            missing_value="",
            style=Pack(height=200, width=800, flex=1),
        )

    def append_line(self, line: str) -> None:
        self.widget.data.insert(0, (line,))
        if len(self.widget.data) > self._max_lines:
            del self.widget.data[self._max_lines]
