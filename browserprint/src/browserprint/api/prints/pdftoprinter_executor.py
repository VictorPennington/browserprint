"""Printing helpers for PDFtoPrinter (pdftoprinter-c) command execution.

PDFtoPrinter is a native Windows utility that renders PDFs with PDFium and
prints them through a GDI printer device context. The printer name is a single
positional argument that comes *after* the PDF path, and flags use ``/``
prefixes (e.g. ``/tray=3``, ``/landscape``, ``/duplex``, ``/s``).

The local API sends print commands already in PDFtoPrinter's format, e.g.::

    "KONICA MINOLTA Universal V4 PCL" /tray=3 /landscape /s

so :func:`run_pdftoprinter_print` parses the command, extracts the printer
name and flags, and assembles the final executable invocation.
"""

import logging
import os
import shlex
import subprocess
from pathlib import Path

from .executor import PrintExecutionError

logger = logging.getLogger("browserprint.api.prints.pdftoprinter")


def _parse_printer_command(printer_command: str) -> tuple[str, list[str]]:
    """Parse a PDFtoPrinter-style print command into ``(printer_name, flags)``.

    The command is expected to contain:
      * a printer name (leading tokens that don't start with ``/``)
      * zero or more ``/``-prefixed flags (e.g. ``/tray=3``, ``/s``)

    Returns a ``(printer_name, flags)`` tuple.

    Example::

        _parse_printer_command('"My Printer" /tray=3 /s')
        # -> ("My Printer", ["/tray=3", "/s"])
    """
    tokens = shlex.split(printer_command, posix=(os.name != "nt"))
    # shlex in Windows mode keeps surrounding quotes, so strip them explicitly.
    tokens = [token.strip().strip('"').strip("'") for token in tokens]
    tokens = [token for token in tokens if token]

    # If the entire command was sent as a single quoted string (e.g.
    # "My Printer /portrait /s"), split on ``/`` to separate printer name
    # from flags.
    if len(tokens) == 1 and "/" in tokens[0]:
        parts = tokens[0].split("/", 1)
        tokens = [parts[0]] + [
            segment if segment.startswith("/") else "/" + segment
            for segment in parts[1].split()
            if segment
        ]

    if not tokens:
        raise PrintExecutionError("printCommand cannot be empty")

    # Printer name = leading tokens up to the first flag (starts with /).
    index = 0
    while index < len(tokens) and not tokens[index].startswith("/"):
        index += 1
    printer_name = " ".join(tokens[:index]).strip()
    if not printer_name:
        raise PrintExecutionError("printCommand must include a printer name")

    flags = list(tokens[index:])
    return printer_name, flags


def run_pdftoprinter_print(
    pdftoprinter_path: Path, printer_command: str, output_path: Path
) -> None:
    """Execute PDFtoPrinter using the print command from the API.

    The ``printer_command`` is parsed to extract the printer name and any
    ``/``-prefixed flags. The final command is assembled as::

        pdftoprinter-c <output_path> <printer_name> [flags...]

    No flags are added automatically; all flags must be provided by the API
    caller (e.g. ``/s`` for silent mode, ``/no-autotray``, etc.).
    """
    if not pdftoprinter_path.exists():
        raise PrintExecutionError(
            f"PDFtoPrinter executable not found at {pdftoprinter_path}"
        )

    printer_name, flags = _parse_printer_command(printer_command)

    command = [str(pdftoprinter_path), str(output_path), printer_name]
    command.extend(flags)

    logger.info("PDFtoPrinter command: %s", subprocess.list2cmdline(command))
    logger.debug("PDFtoPrinter argv: %s", command)

    try:
        result = subprocess.run(
            command,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise PrintExecutionError(
            f"Failed to execute PDFtoPrinter command: {exc}"
        ) from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        detail = stderr or stdout or "Unknown PDFtoPrinter error"
        raise PrintExecutionError(f"PDFtoPrinter print command failed: {detail}")
