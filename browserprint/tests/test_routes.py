from pathlib import Path

from browserprint.api.pdf_fetcher import PDFDownloadError
from browserprint.api.server import create_app
from fastapi.testclient import TestClient


def test_print_requires_url_and_print_command() -> None:
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
            "printCommand": "MyPrinter",
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
            "printCommand": "ZDesigner GK420d",
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert response.json()["requestId"]
    assert called["url"] == "http://localhost:8000/test/invoice"
    saved = tmp_path / "invoice.pdf"
    assert saved.exists()
    assert saved.read_bytes().startswith(b"%PDF")


def test_print_download_errors_do_not_fail_http_ack(
    monkeypatch, tmp_path: Path
) -> None:
    client = TestClient(create_app())

    def fake_fetch_pdf(url: str) -> bytes:
        raise PDFDownloadError("download failed")

    monkeypatch.setattr("browserprint.api.routes.fetch_pdf", fake_fetch_pdf)
    monkeypatch.setattr("browserprint.api.routes._DEBUG_OUTPUT_DIR", tmp_path)

    response = client.post(
        "/print",
        json={
            "pdfUrl": "http://localhost:8000/test.pdf",
            "printCommand": "MyPrinter",
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


def test_print_returns_503_when_download_queue_is_full() -> None:
    client = TestClient(create_app())

    from browserprint.api import routes

    original = routes._try_acquire_download_slot
    routes._try_acquire_download_slot = lambda: False
    try:
        response = client.post(
            "/print",
            json={
                "pdfUrl": "http://localhost:8000/test.pdf",
                "printCommand": "MyPrinter",
            },
        )
    finally:
        routes._try_acquire_download_slot = original

    assert response.status_code == 503


def test_print_jobs_requires_non_empty_jobs_array() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/print/jobs",
        json={"jobs": []},
    )

    assert response.status_code == 422


def test_print_jobs_downloads_and_saves_all_pdfs(monkeypatch, tmp_path: Path) -> None:
    client = TestClient(create_app())

    called_urls: list[str] = []

    def fake_fetch_pdf(url: str) -> bytes:
        called_urls.append(url)
        return b"%PDF-fake-content"

    monkeypatch.setattr("browserprint.api.routes.fetch_pdf", fake_fetch_pdf)
    monkeypatch.setattr("browserprint.api.routes._DEBUG_OUTPUT_DIR", tmp_path)

    response = client.post(
        "/print/jobs",
        json={
            "jobs": [
                {
                    "pdfUrl": "http://localhost:8000/test/invoice-a",
                    "printCommand": "Printer A",
                },
                {
                    "pdfUrl": "http://localhost:8000/test/invoice-b",
                    "printCommand": "Printer B",
                },
            ]
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert response.json()["requestId"]
    assert response.json()["acceptedJobs"] == "2"
    assert called_urls == [
        "http://localhost:8000/test/invoice-a",
        "http://localhost:8000/test/invoice-b",
    ]
    assert (tmp_path / "invoice-a.pdf").exists()
    assert (tmp_path / "invoice-b.pdf").exists()
