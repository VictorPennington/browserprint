from datetime import datetime
from pathlib import Path

from browserprint.api.pdf_fetcher import PDFDownloadError
from browserprint.api.server import create_app
from fastapi.testclient import TestClient


class FrozenDateTime:
    @classmethod
    def now(cls) -> datetime:
        return datetime(2025, 12, 1, 12, 35)


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
            "customerNumber": "CUST1",
            "invoiceNumber": "INV1",
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
    monkeypatch.setattr("browserprint.api.routes.datetime", FrozenDateTime)

    response = client.post(
        "/print",
        json={
            "pdfUrl": "http://localhost:8000/test/invoice",
            "printCommand": "ZDesigner GK420d",
            "customerNumber": "123",
            "invoiceNumber": "456",
        },
    )

    from browserprint.api import routes as _routes

    _routes._DOWNLOAD_QUEUE.join()

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert response.json()["requestId"]
    assert called["url"] == "http://localhost:8000/test/invoice"
    saved = tmp_path / "2025_12_01_1235_123_456_invoice.pdf"
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
    monkeypatch.setattr("browserprint.api.routes.datetime", FrozenDateTime)

    response = client.post(
        "/print",
        json={
            "pdfUrl": "http://localhost:8000/test.pdf",
            "printCommand": "MyPrinter",
            "customerNumber": "123",
            "invoiceNumber": "456",
        },
    )

    from browserprint.api import routes as _routes

    _routes._DOWNLOAD_QUEUE.join()

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"


def test_print_accepts_empty_customer_and_invoice_numbers(
    monkeypatch, tmp_path: Path
) -> None:
    client = TestClient(create_app())

    def fake_fetch_pdf(url: str) -> bytes:
        return b"%PDF-fake-content"

    monkeypatch.setattr("browserprint.api.routes.fetch_pdf", fake_fetch_pdf)
    monkeypatch.setattr("browserprint.api.routes._DEBUG_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr("browserprint.api.routes.datetime", FrozenDateTime)

    response = client.post(
        "/print",
        json={
            "pdfUrl": "http://localhost:8000/test/invoice",
            "printCommand": "MyPrinter",
            "customerNumber": "",
            "invoiceNumber": "",
        },
    )

    from browserprint.api import routes as _routes

    _routes._DOWNLOAD_QUEUE.join()

    assert response.status_code == 202
    assert (tmp_path / "2025_12_01_1235_____invoice.pdf").exists()


def test_print_accepts_null_customer_and_invoice_numbers(
    monkeypatch, tmp_path: Path
) -> None:
    client = TestClient(create_app())

    def fake_fetch_pdf(url: str) -> bytes:
        return b"%PDF-fake-content"

    monkeypatch.setattr("browserprint.api.routes.fetch_pdf", fake_fetch_pdf)
    monkeypatch.setattr("browserprint.api.routes._DEBUG_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr("browserprint.api.routes.datetime", FrozenDateTime)

    response = client.post(
        "/print",
        json={
            "pdfUrl": "http://localhost:8000/test/invoice",
            "printCommand": "MyPrinter",
            "customerNumber": None,
            "invoiceNumber": None,
        },
    )

    from browserprint.api import routes as _routes

    _routes._DOWNLOAD_QUEUE.join()

    assert response.status_code == 202
    assert (tmp_path / "2025_12_01_1235_____invoice.pdf").exists()


def test_print_accepts_integer_customer_and_invoice_numbers(
    monkeypatch, tmp_path: Path
) -> None:
    client = TestClient(create_app())

    def fake_fetch_pdf(url: str) -> bytes:
        return b"%PDF-fake-content"

    monkeypatch.setattr("browserprint.api.routes.fetch_pdf", fake_fetch_pdf)
    monkeypatch.setattr("browserprint.api.routes._DEBUG_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr("browserprint.api.routes.datetime", FrozenDateTime)

    response = client.post(
        "/print",
        json={
            "pdfUrl": "http://localhost:8000/test/invoice",
            "printCommand": "MyPrinter",
            "customerNumber": 123,
            "invoiceNumber": 456,
        },
    )

    from browserprint.api import routes as _routes

    _routes._DOWNLOAD_QUEUE.join()

    assert response.status_code == 202
    assert (tmp_path / "2025_12_01_1235_123_456_invoice.pdf").exists()


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
    monkeypatch.setattr("browserprint.api.routes.datetime", FrozenDateTime)

    response = client.post(
        "/print/jobs",
        json={
            "customerNumber": "111",
            "invoiceNumber": "1001",
            "jobs": [
                {
                    "pdfUrl": "http://localhost:8000/test/invoice-a",
                    "printCommand": "Printer A",
                },
                {
                    "pdfUrl": "http://localhost:8000/test/invoice-b",
                    "printCommand": "Printer B",
                },
            ],
        },
    )

    from browserprint.api import routes as _routes

    _routes._DOWNLOAD_QUEUE.join()

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert response.json()["requestId"]
    assert response.json()["acceptedJobs"] == "2"
    assert called_urls == [
        "http://localhost:8000/test/invoice-a",
        "http://localhost:8000/test/invoice-b",
    ]
    assert (tmp_path / "2025_12_01_1235_111_1001_invoice-a.pdf").exists()
    assert (tmp_path / "2025_12_01_1235_111_1001_invoice-b.pdf").exists()


def test_print_jobs_accepts_null_customer_and_invoice_numbers(
    monkeypatch, tmp_path: Path
) -> None:
    client = TestClient(create_app())

    def fake_fetch_pdf(url: str) -> bytes:
        return b"%PDF-fake-content"

    monkeypatch.setattr("browserprint.api.routes.fetch_pdf", fake_fetch_pdf)
    monkeypatch.setattr("browserprint.api.routes._DEBUG_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr("browserprint.api.routes.datetime", FrozenDateTime)

    response = client.post(
        "/print/jobs",
        json={
            "customerNumber": None,
            "invoiceNumber": None,
            "jobs": [
                {
                    "pdfUrl": "http://localhost:8000/test/envelope",
                    "printCommand": "Printer A",
                }
            ],
        },
    )

    from browserprint.api import routes as _routes

    _routes._DOWNLOAD_QUEUE.join()

    assert response.status_code == 202
    assert (tmp_path / "2025_12_01_1235_____envelope.pdf").exists()


def test_print_jobs_accepts_integer_customer_and_invoice_numbers(
    monkeypatch, tmp_path: Path
) -> None:
    client = TestClient(create_app())

    def fake_fetch_pdf(url: str) -> bytes:
        return b"%PDF-fake-content"

    monkeypatch.setattr("browserprint.api.routes.fetch_pdf", fake_fetch_pdf)
    monkeypatch.setattr("browserprint.api.routes._DEBUG_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr("browserprint.api.routes.datetime", FrozenDateTime)

    response = client.post(
        "/print/jobs",
        json={
            "customerNumber": 111,
            "invoiceNumber": 2002,
            "jobs": [
                {
                    "pdfUrl": "http://localhost:8000/test/envelope",
                    "printCommand": "Printer A",
                }
            ],
        },
    )

    from browserprint.api import routes as _routes

    _routes._DOWNLOAD_QUEUE.join()

    assert response.status_code == 202
    assert (tmp_path / "2025_12_01_1235_111_2002_envelope.pdf").exists()


def test_resolve_output_path_appends_counter_when_name_already_exists(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("browserprint.api.routes._DEBUG_OUTPUT_DIR", tmp_path)
    monkeypatch.setattr("browserprint.api.routes.datetime", FrozenDateTime)

    first_path = tmp_path / "2025_12_01_1235_123_456_invoice.pdf"
    first_path.write_bytes(b"existing")

    from browserprint.api.routes import _resolve_output_path

    resolved = _resolve_output_path("http://localhost:8000/test/invoice", "123", "456")

    assert resolved == tmp_path / "2025_12_01_1235_123_456_invoice_2.pdf"
