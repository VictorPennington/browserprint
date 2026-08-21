"""Printing helpers for PDFtoPrinter (pdftoprinter-c) command execution.

PDFtoPrinter is a native Windows utility that renders PDFs with PDFium and
prints them through a GDI printer device context. Unlike Sumatra, the printer
name is a single positional argument that comes *after* the PDF path, and any
extra positional arguments are interpreted as additional PDF files. For that
reason the parsed printer command is joined back into one argument here.
"""

import subprocess
from pathlib import Path

from .executor import PrintExecutionError, _parse_printer_command


def run_pdftoprinter_print(
    pdftoprinter_path: Path, printer_command: str, output_path: Path
) -> None:
    """Execute PDFtoPrinter in silent mode with the parsed printer name.

    ``/s`` runs silently and ``/no-autotray`` keeps unattended printing from
    pausing when a page's paper size is not loaded in the printer.
    """
    if not pdftoprinter_path.exists():
        raise PrintExecutionError(
            f"PDFtoPrinter executable not found at {pdftoprinter_path}"
        )

    printer_name = " ".join(_parse_printer_command(printer_command))
    command = [
        str(pdftoprinter_path),
        str(output_path),
        printer_name,
        "/s",
        "/no-autotray",
    ]

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
