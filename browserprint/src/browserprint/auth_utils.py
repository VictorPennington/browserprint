"""Auth-related utility helpers independent from UI frameworks."""

from __future__ import annotations

import textwrap
from urllib.parse import urlparse


def validate_base_url(base_url: str) -> str:
    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            "Invalid API Base URL. Use a full URL like http://localhost or https://example.com"
        )
    return base_url.rstrip("/")


def wrap_status_message(message: str, width: int = 68) -> str:
    lines = []
    for raw_line in str(message).splitlines() or [""]:
        wrapped = textwrap.wrap(raw_line, width=width) or [""]
        lines.extend(wrapped)
    return "\n".join(lines)
