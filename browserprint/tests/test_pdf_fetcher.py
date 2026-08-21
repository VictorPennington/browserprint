import pytest
import requests
from browserprint.api.downloads.fetcher import PDFDownloadError, fetch_pdf


class DummyResponse:
    def __init__(self, status_code: int, headers: dict[str, str], content: bytes):
        self.status_code = status_code
        self.headers = headers
        self.content = content


def test_fetch_pdf_requires_bearer_token(monkeypatch) -> None:
    monkeypatch.delenv("BROWSERPRINT_LARAVEL_TOKEN", raising=False)
    monkeypatch.setattr(
        "browserprint.api.downloads.fetcher._AUTH_STORE.get_token",
        lambda: None,
    )

    with pytest.raises(PDFDownloadError) as exc_info:
        fetch_pdf("http://localhost:8000/doc.pdf")

    assert "BROWSERPRINT_LARAVEL_TOKEN" in str(exc_info.value)


def test_fetch_pdf_uses_bearer_token_header(monkeypatch) -> None:
    monkeypatch.setenv("BROWSERPRINT_LARAVEL_TOKEN", "abc123")
    monkeypatch.setattr(
        "browserprint.api.downloads.fetcher._AUTH_STORE.get_token",
        lambda: None,
    )

    captured = {}

    def fake_get(url: str, headers: dict[str, str], timeout: int):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return DummyResponse(
            status_code=200,
            headers={"content-type": "application/pdf"},
            content=b"%PDF-fake",
        )

    monkeypatch.setattr("browserprint.api.downloads.fetcher.requests.get", fake_get)

    payload = fetch_pdf("http://localhost:8000/doc.pdf")

    assert payload.startswith(b"%PDF")
    assert captured["url"] == "http://localhost:8000/doc.pdf"
    assert captured["headers"]["Authorization"] == "Bearer abc123"


def test_fetch_pdf_rejects_non_pdf(monkeypatch) -> None:
    monkeypatch.setenv("BROWSERPRINT_LARAVEL_TOKEN", "abc123")
    monkeypatch.setattr(
        "browserprint.api.downloads.fetcher._AUTH_STORE.get_token",
        lambda: None,
    )

    def fake_get(url: str, headers: dict[str, str], timeout: int):
        return DummyResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            content=b'{"ok":true}',
        )

    monkeypatch.setattr("browserprint.api.downloads.fetcher.requests.get", fake_get)

    with pytest.raises(PDFDownloadError) as exc_info:
        fetch_pdf("http://localhost:8000/doc.pdf")

    assert "did not return a PDF" in str(exc_info.value)


def test_fetch_pdf_accepts_explicit_token_without_env(monkeypatch) -> None:
    monkeypatch.delenv("BROWSERPRINT_LARAVEL_TOKEN", raising=False)

    captured = {}

    def fake_get(url: str, headers: dict[str, str], timeout: int):
        captured["headers"] = headers
        return DummyResponse(
            status_code=200,
            headers={"content-type": "application/pdf"},
            content=b"%PDF-fake",
        )

    monkeypatch.setattr("browserprint.api.downloads.fetcher.requests.get", fake_get)

    payload = fetch_pdf("http://localhost:8000/doc.pdf", token="ui-token")

    assert payload.startswith(b"%PDF")
    assert captured["headers"]["Authorization"] == "Bearer ui-token"


def test_fetch_pdf_handles_request_exception(monkeypatch) -> None:
    monkeypatch.setenv("BROWSERPRINT_LARAVEL_TOKEN", "abc123")
    monkeypatch.setattr(
        "browserprint.api.downloads.fetcher._AUTH_STORE.get_token",
        lambda: None,
    )

    def fake_get(url: str, headers: dict[str, str], timeout: int):
        raise requests.Timeout("timed out")

    monkeypatch.setattr("browserprint.api.downloads.fetcher.requests.get", fake_get)

    with pytest.raises(PDFDownloadError) as exc_info:
        fetch_pdf("http://localhost:8000/doc.pdf")

    assert "Failed to fetch PDF" in str(exc_info.value)


def test_fetch_pdf_prefers_stored_token_for_authorization_header(monkeypatch) -> None:
    monkeypatch.setenv("BROWSERPRINT_LARAVEL_TOKEN", "env-token")
    monkeypatch.setattr(
        "browserprint.api.downloads.fetcher._AUTH_STORE.get_token",
        lambda: "stored-token",
    )

    captured = {}

    def fake_get(url: str, headers: dict[str, str], timeout: int):
        captured["headers"] = headers
        return DummyResponse(
            status_code=200,
            headers={"content-type": "application/pdf"},
            content=b"%PDF-fake",
        )

    monkeypatch.setattr("browserprint.api.downloads.fetcher.requests.get", fake_get)

    payload = fetch_pdf("http://localhost:8000/doc.pdf")

    assert payload.startswith(b"%PDF")
    assert captured["headers"]["Authorization"] == "Bearer stored-token"
