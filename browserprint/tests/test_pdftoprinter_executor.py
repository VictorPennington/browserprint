from pathlib import Path

import pytest
from browserprint.api.prints.pdftoprinter_executor import (
    PrintExecutionError,
    _parse_printer_command,
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

    run_pdftoprinter_print(fake_exe, '"My Printer" /s', fake_pdf)

    assert captured["shell"] is False
    command = captured["command"]
    assert command[0].endswith("PDFtoPrinterNative.exe")
    assert command[1].endswith("ticket.pdf")
    # Printer name is a single positional argument after the PDF path.
    assert command[2] == "My Printer"
    # /s is passed through from the API command.
    assert "/s" in command


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

    run_pdftoprinter_print(fake_exe, "My Printer /s", fake_pdf)

    # Unquoted multi-word names must collapse into one argument so they are
    # not mistaken for extra PDF files.
    assert captured["command"][2] == "My Printer"
    assert "/s" in captured["command"]


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
        run_pdftoprinter_print(fake_exe, '"My Printer" /s', fake_pdf)

    assert "printer offline" in str(exc_info.value)


def test_run_pdftoprinter_print_requires_existing_exe(tmp_path) -> None:
    fake_pdf = tmp_path / "ticket.pdf"
    fake_pdf.write_bytes(b"%PDF-fake")

    with pytest.raises(PrintExecutionError) as exc_info:
        run_pdftoprinter_print(Path("missing.exe"), "MyPrinter /s", fake_pdf)

    assert "not found" in str(exc_info.value)


def test_parse_printer_command_printer_only() -> None:
    name, flags = _parse_printer_command('"My Printer"')
    assert name == "My Printer"
    assert flags == []


def test_parse_printer_command_with_flags() -> None:
    name, flags = _parse_printer_command(
        '"KONICA MINOLTA Universal V4 PCL" /tray=3 /landscape /s'
    )
    assert name == "KONICA MINOLTA Universal V4 PCL"
    assert flags == ["/tray=3", "/landscape", "/s"]


def test_parse_printer_command_no_autotray_flag() -> None:
    name, flags = _parse_printer_command('"My Printer" /no-autotray /s')
    assert name == "My Printer"
    assert flags == ["/no-autotray", "/s"]


def test_parse_printer_command_requires_printer_name() -> None:
    with pytest.raises(PrintExecutionError):
        _parse_printer_command("/tray=3")


def test_parse_printer_command_empty_raises() -> None:
    with pytest.raises(PrintExecutionError):
        _parse_printer_command("")


def test_parse_printer_command_single_quoted_string() -> None:
    """API may send the entire command as a single quoted string."""
    name, flags = _parse_printer_command(
        '"KONICA MINOLTA Universal V4 PCL /portrait /no-autotray"'
    )
    assert name == "KONICA MINOLTA Universal V4 PCL"
    assert flags == ["/portrait", "/no-autotray"]


def test_run_pdftoprinter_print_passes_all_flags_through(monkeypatch, tmp_path) -> None:
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

    run_pdftoprinter_print(
        fake_exe,
        '"KONICA MINOLTA Universal V4 PCL" /tray=3 /landscape /duplex /s',
        fake_pdf,
    )

    command = captured["command"]
    assert command[0].endswith("PDFtoPrinterNative.exe")
    assert command[1].endswith("ticket.pdf")
    assert command[2] == "KONICA MINOLTA Universal V4 PCL"
    assert "/tray=3" in command
    assert "/landscape" in command
    assert "/duplex" in command
    assert "/s" in command


def test_run_pdftoprinter_print_no_flags_added_automatically(
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

    run_pdftoprinter_print(fake_exe, '"My Printer"', fake_pdf)

    # Only the executable, PDF path, and printer name should be in the command.
    assert len(captured["command"]) == 3
    assert captured["command"][2] == "My Printer"
