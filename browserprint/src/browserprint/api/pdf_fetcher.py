"""PDF download helpers for authenticated Laravel endpoints."""

import os

import requests


class PDFDownloadError(RuntimeError):
    """Raised when a PDF cannot be downloaded or validated."""


def _get_required_bearer_token() -> str:
    token = os.getenv("BROWSERPRINT_LARAVEL_TOKEN", "").strip()
    if not token:
        raise PDFDownloadError(
            "Missing Laravel bearer token. Configure BROWSERPRINT_LARAVEL_TOKEN in .env"
        )
    return token


def _resolve_bearer_token(token: str | None) -> str:
    if token is None:
        return _get_required_bearer_token()

    normalized = token.strip()
    if not normalized:
        raise PDFDownloadError("Missing bearer token for PDF request")
    return normalized


def fetch_pdf(url: str, token: str | None = None) -> bytes:
    """Download a PDF from URL using Sanctum bearer token from environment."""
    timeout_seconds = int(os.getenv("BROWSERPRINT_DOWNLOAD_TIMEOUT_SECONDS", "20"))
    max_pdf_bytes = int(os.getenv("BROWSERPRINT_MAX_PDF_BYTES", str(10 * 1024 * 1024)))
    auth_header = os.getenv("BROWSERPRINT_LARAVEL_AUTH_HEADER", "Authorization")
    bearer_token = _resolve_bearer_token(token)

    headers = {
        auth_header: f"Bearer {bearer_token}",
        "Accept": "application/pdf",
    }

    try:
        response = requests.get(url, headers=headers, timeout=timeout_seconds)
    except requests.RequestException as exc:
        raise PDFDownloadError(f"Failed to fetch PDF from URL: {exc}") from exc

    if response.status_code in {401, 403}:
        raise PDFDownloadError("Laravel rejected authentication for PDF request")

    if response.status_code >= 400:
        raise PDFDownloadError(
            f"PDF request failed with status code {response.status_code}"
        )

    content_type = (response.headers.get("content-type") or "").lower()
    content = response.content

    if len(content) > max_pdf_bytes:
        raise PDFDownloadError("Downloaded PDF exceeded configured maximum size")

    if "application/pdf" not in content_type and not content.startswith(b"%PDF"):
        raise PDFDownloadError("URL did not return a PDF document")

    return content
