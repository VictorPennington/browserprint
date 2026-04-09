from pathlib import Path

from browserprint.api.pdf_fetcher import PDFDownloadError
from browserprint.api.server import create_app
from fastapi.testclient import TestClient


def test_print_requires_url_and_printer_command() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/print",
        json={
            "filename": "ticket.pdf",
        },
    )

    assert response.status_code == 422


def test_print_rejects_non_http_url() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/print",
        json={
            "pdfUrl": "file:///tmp/test.pdf",
            "printerCommand": "MyPrinter",
            "filename": "ticket.pdf",
        },
    )

    assert response.status_code == 422


def test_print_downloads_and_runs_sumatra(monkeypatch) -> None:
    client = TestClient(create_app())

    called = {}

    def fake_fetch_pdf(url: str) -> bytes:
        called["url"] = url
        return b"%PDF-fake-content"

    def fake_run_sumatra_print(
        sumatra_path: Path, printer_command: str, output_path: Path
    ) -> None:
        called["sumatra_path"] = str(sumatra_path)
        called["printer_command"] = printer_command
        called["output_path"] = output_path

    monkeypatch.setattr("browserprint.api.routes.fetch_pdf", fake_fetch_pdf)
    monkeypatch.setattr(
        "browserprint.api.routes.run_sumatra_print", fake_run_sumatra_print
    )

    response = client.post(
        "/print",
        json={
            "pdfUrl": "http://localhost:8000/test.pdf",
            "printerCommand": "ZDesigner GK420d",
            "filename": "ticket.pdf",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "printed"
    assert called["url"] == "http://localhost:8000/test.pdf"
    assert called["printer_command"] == "ZDesigner GK420d"
    assert called["output_path"].name == "ticket.pdf"


def test_print_returns_502_for_download_errors(monkeypatch) -> None:
    client = TestClient(create_app())

    def fake_fetch_pdf(url: str) -> bytes:
        raise PDFDownloadError("download failed")

    monkeypatch.setattr("browserprint.api.routes.fetch_pdf", fake_fetch_pdf)

    response = client.post(
        "/print",
        json={
            "pdfUrl": "http://localhost:8000/test.pdf",
            "printerCommand": "MyPrinter",
            "filename": "ticket.pdf",
        },
    )

    assert response.status_code == 502
