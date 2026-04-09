from pathlib import Path

from browserprint.api.pdf_fetcher import PDFDownloadError
from browserprint.api.server import create_app
from fastapi.testclient import TestClient


def test_print_requires_url_and_printer_command() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/print",
        json={
            "pdfUrl": "http://localhost:8000/test.pdf",
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
        },
    )

    assert response.status_code == 422


def test_print_downloads_and_saves_pdf(monkeypatch, tmp_path: Path) -> None:
    client = TestClient(create_app())

    called = {}

    def fake_fetch_pdf(url: str) -> bytes:
        called["url"] = url
        return b"%PDF-fake-content"

    monkeypatch.setattr("browserprint.api.routes.fetch_pdf", fake_fetch_pdf)
    monkeypatch.setattr("browserprint.api.routes._DEBUG_OUTPUT_DIR", tmp_path)

    response = client.post(
        "/print",
        json={
            "pdfUrl": "http://localhost:8000/test/invoice",
            "printerCommand": "ZDesigner GK420d",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "downloaded"
    assert response.json()["filename"] == "invoice.pdf"
    assert called["url"] == "http://localhost:8000/test/invoice"
    saved = tmp_path / "invoice.pdf"
    assert saved.exists()
    assert saved.read_bytes().startswith(b"%PDF")


def test_print_returns_502_for_download_errors(monkeypatch, tmp_path: Path) -> None:
    client = TestClient(create_app())

    def fake_fetch_pdf(url: str) -> bytes:
        raise PDFDownloadError("download failed")

    monkeypatch.setattr("browserprint.api.routes.fetch_pdf", fake_fetch_pdf)
    monkeypatch.setattr("browserprint.api.routes._DEBUG_OUTPUT_DIR", tmp_path)

    response = client.post(
        "/print",
        json={
            "pdfUrl": "http://localhost:8000/test.pdf",
            "printerCommand": "MyPrinter",
        },
    )

    assert response.status_code == 502
