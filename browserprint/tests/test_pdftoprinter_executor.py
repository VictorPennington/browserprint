from pathlib import Path

import pytest
from browserprint.api.prints.pdftoprinter_executor import (
    PrintExecutionError,
    run_pdftoprinter_print,
)


class DummyResult:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_run_pdftoprinter_print_builds_expected_command(monkeypatch, tmp_path) -> None:
    fake_exe = tmp_path / "PDFtoPrinterNative.exe"
    fake_exe.write_text("fake")
    fake_pdf = tmp_path / "ticket.pdf"
    fake_pdf.write_bytes(b"%PDF-fake")

    captured = {}

    def fake_run(command, shell, check, capture_output, text):
        captured["command"] = command
        captured["shell"] = shell
        return DummyResult(returncode=0)

    monkeypatch.setattr(
        "browserprint.api.prints.pdftoprinter_executor.subprocess.run", fake_run
    )

    run_pdftoprinter_print(fake_exe, '"My Printer"', fake_pdf)

    assert captured["shell"] is False
    command = captured["command"]
    assert command[0].endswith("PDFtoPrinterNative.exe")
    assert command[1].endswith("ticket.pdf")
    # Printer name is a single positional argument after the PDF path.
    assert command[2] == "My Printer"
    assert "/s" in command
    assert "/no-autotray" in command


def test_run_pdftoprinter_print_joins_unquoted_printer_name(
    monkeypatch, tmp_path
) -> None:
    fake_exe = tmp_path / "PDFtoPrinterNative.exe"
    fake_exe.write_text("fake")
    fake_pdf = tmp_path / "ticket.pdf"
    fake_pdf.write_bytes(b"%PDF-fake")

    captured = {}

    def fake_run(command, shell, check, capture_output, text):
        captured["command"] = command
        return DummyResult(returncode=0)

    monkeypatch.setattr(
        "browserprint.api.prints.pdftoprinter_executor.subprocess.run", fake_run
    )

    run_pdftoprinter_print(fake_exe, "My Printer", fake_pdf)

    # Unquoted multi-word names must collapse into one argument so they are
    # not mistaken for extra PDF files.
    assert captured["command"][2] == "My Printer"


def test_run_pdftoprinter_print_raises_on_process_failure(
    monkeypatch, tmp_path
) -> None:
    fake_exe = tmp_path / "PDFtoPrinterNative.exe"
    fake_exe.write_text("fake")
    fake_pdf = tmp_path / "ticket.pdf"
    fake_pdf.write_bytes(b"%PDF-fake")

    def fake_run(command, shell, check, capture_output, text):
        return DummyResult(returncode=1, stderr="printer offline")

    monkeypatch.setattr(
        "browserprint.api.prints.pdftoprinter_executor.subprocess.run", fake_run
    )

    with pytest.raises(PrintExecutionError) as exc_info:
        run_pdftoprinter_print(fake_exe, '"My Printer"', fake_pdf)

    assert "printer offline" in str(exc_info.value)


def test_run_pdftoprinter_print_requires_existing_exe(tmp_path) -> None:
    fake_pdf = tmp_path / "ticket.pdf"
    fake_pdf.write_bytes(b"%PDF-fake")

    with pytest.raises(PrintExecutionError) as exc_info:
        run_pdftoprinter_print(Path("missing.exe"), "MyPrinter", fake_pdf)

    assert "not found" in str(exc_info.value)
