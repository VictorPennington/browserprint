"""Printing helpers for Sumatra command execution."""

import os
import shlex
import subprocess
from pathlib import Path


class PrintExecutionError(RuntimeError):
    """Raised when Sumatra print execution fails."""


def _parse_printer_command(printer_command: str) -> list[str]:
    tokens = shlex.split(printer_command, posix=(os.name != "nt"))
    tokens = [token.strip().strip('"').strip("'") for token in tokens]
    if not tokens:
        raise PrintExecutionError("printerCommand cannot be empty")
    if tokens[-1].lower().endswith(".pdf"):
        tokens = tokens[:-1]
    return tokens


def run_sumatra_print(
    sumatra_path: Path, printer_command: str, output_path: Path
) -> None:
    """Execute Sumatra in silent mode with parsed printer command arguments."""
    if not sumatra_path.exists():
        raise PrintExecutionError(f"Sumatra executable not found at {sumatra_path}")

    command_parts = _parse_printer_command(printer_command)
    command = [str(sumatra_path), "-print-to", *command_parts, str(output_path)]

    try:
        result = subprocess.run(
            command,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise PrintExecutionError(f"Failed to execute Sumatra command: {exc}") from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        detail = stderr or stdout or "Unknown Sumatra error"
        raise PrintExecutionError(f"Sumatra print command failed: {detail}")
