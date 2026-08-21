from pathlib import Path

import pytest
from browserprint.api.prints.executor import (
    PrintExecutionError,
    _parse_printer_command,
    run_sumatra_print,
)


class DummyResult:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_parse_printer_command_drops_trailing_pdf() -> None:
    parsed = _parse_printer_command('"My Printer" C:/temp/old.pdf')
    assert parsed == ["My Printer"]


def test_run_sumatra_print_builds_expected_command(monkeypatch, tmp_path) -> None:
    fake_sumatra = tmp_path / "SumatraPDF-3.6-64.exe"
    fake_sumatra.write_text("fake")
    fake_pdf = tmp_path / "ticket.pdf"
    fake_pdf.write_bytes(b"%PDF-fake")

    captured = {}

    def fake_run(command, shell, check, capture_output, text):
        captured["command"] = command
        captured["shell"] = shell
        return DummyResult(returncode=0)

    monkeypatch.setattr("browserprint.api.prints.executor.subprocess.run", fake_run)

    run_sumatra_print(fake_sumatra, '"My Printer"', fake_pdf)

    assert captured["shell"] is False
    assert captured["command"][0].endswith("SumatraPDF-3.6-64.exe")
    assert captured["command"][-1].endswith("ticket.pdf")


def test_run_sumatra_print_raises_on_process_failure(monkeypatch, tmp_path) -> None:
    fake_sumatra = tmp_path / "SumatraPDF-3.6-64.exe"
    fake_sumatra.write_text("fake")
    fake_pdf = tmp_path / "ticket.pdf"
    fake_pdf.write_bytes(b"%PDF-fake")

    def fake_run(command, shell, check, capture_output, text):
        return DummyResult(returncode=1, stderr="printer offline")

    monkeypatch.setattr("browserprint.api.prints.executor.subprocess.run", fake_run)

    with pytest.raises(PrintExecutionError) as exc_info:
        run_sumatra_print(fake_sumatra, '"My Printer"', fake_pdf)

    assert "printer offline" in str(exc_info.value)


def test_run_sumatra_print_requires_existing_sumatra(tmp_path) -> None:
    fake_pdf = tmp_path / "ticket.pdf"
    fake_pdf.write_bytes(b"%PDF-fake")

    with pytest.raises(PrintExecutionError) as exc_info:
        run_sumatra_print(Path("missing.exe"), "MyPrinter", fake_pdf)

    assert "not found" in str(exc_info.value)
