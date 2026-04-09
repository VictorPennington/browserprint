"""Manual PDF download window for authenticated endpoint testing."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import toga
from toga.constants import COLUMN, ROW
from toga.style import Pack

from browserprint.api.pdf_fetcher import PDFDownloadError, fetch_pdf
from browserprint.auth_config import AuthConfigStore
from browserprint.auth_utils import validate_base_url, wrap_status_message

logger = logging.getLogger("browserprint.ui.download_pdf")

_DEFAULT_OUTPUT_DIR = Path.home() / "Desktop" / "debug_pdfs"


class DownloadPdfController:
    """Manage a manual PDF download UI backed by persisted auth configuration."""

    def __init__(
        self,
        app: toga.App,
        log_line: Callable[[str], None],
        auth_store: AuthConfigStore | None = None,
        pdf_fetcher: Callable[[str, str | None], bytes] | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self.app = app
        self.log_line = log_line
        self.auth_store = auth_store or AuthConfigStore()
        self.pdf_fetcher = pdf_fetcher or fetch_pdf
        self.output_dir = output_dir or _DEFAULT_OUTPUT_DIR
        self.auth_config = self.auth_store.load()
        self.download_window = None

    def open(self, widget=None) -> None:
        self.auth_config = self.auth_store.load()

        if self.download_window is None:
            self._build_window()

        self._refresh_values()
        self.download_window.show()

    def _build_window(self) -> None:
        content = toga.Box(style=Pack(direction=COLUMN, padding=12, gap=8))

        content.add(toga.Label("Saved API Base URL"))
        self.base_url_value = toga.Label("", style=Pack(padding_bottom=4))
        content.add(self.base_url_value)

        content.add(toga.Label("PDF Endpoint Path (or full URL)"))
        self.endpoint_input = toga.TextInput(
            value="/api/browserprint/pdf",
            placeholder="/api/browserprint/documents/123",
            style=Pack(flex=1),
        )
        content.add(self.endpoint_input)

        button_row = toga.Box(style=Pack(direction=ROW, padding_top=8, gap=8))
        self.download_button = toga.Button("Download", on_press=self._download_pdf)
        button_row.add(self.download_button)
        content.add(button_row)

        self.download_status_output = toga.MultilineTextInput(
            readonly=True,
            value="Ready to download a PDF.",
            style=Pack(padding_top=6, height=120, flex=0),
        )
        content.add(self.download_status_output)

        self.download_window = toga.Window(title="Download PDF")
        self.download_window.content = content

    def _refresh_values(self) -> None:
        self.base_url_value.text = self.auth_config.api_base_url
        self._set_status(
            "Loaded auth settings. "
            f"Token present={self.auth_config.token_present}, storage={self.auth_config.token_storage}."
        )

    def _download_pdf(self, widget=None) -> None:
        self.auth_config = self.auth_store.load()
        token = self.auth_store.get_token()
        if not token:
            self._set_status("No token available. Generate token first.")
            self.log_line("Download PDF aborted: no stored token.")
            return

        endpoint_path = (self.endpoint_input.value or "").strip()
        if not endpoint_path:
            self._set_status("PDF endpoint is required.")
            self.log_line("Download PDF aborted: endpoint is empty.")
            return

        try:
            url = self._build_url(
                base_url=self.auth_config.api_base_url,
                endpoint_path=endpoint_path,
            )
        except ValueError as exc:
            self._set_status(str(exc))
            self.log_line(f"Download PDF aborted: {exc}")
            return

        self._set_download_enabled(False)
        self._set_status("Downloading PDF...")

        threading.Thread(
            target=self._download_worker,
            args=(url, token),
            daemon=True,
            name="browserprint-download-pdf",
        ).start()

    def _download_worker(self, url: str, token: str) -> None:
        try:
            pdf_bytes = self.pdf_fetcher(url, token)
            output_path = self._write_pdf(url, pdf_bytes)
            self.app.loop.call_soon_threadsafe(
                self._on_download_success, url, output_path, len(pdf_bytes)
            )
        except PDFDownloadError as exc:
            self.app.loop.call_soon_threadsafe(self._on_download_error, str(exc))
        except OSError as exc:
            self.app.loop.call_soon_threadsafe(
                self._on_download_error,
                f"Failed to save downloaded PDF: {exc}",
            )
        except Exception:
            logger.exception("Unexpected PDF download failure")
            self.app.loop.call_soon_threadsafe(
                self._on_download_error,
                "PDF download failed due to unexpected error",
            )

    def _on_download_success(
        self, url: str, output_path: Path, size_bytes: int
    ) -> None:
        self._set_status(
            f"Download completed ({size_bytes} bytes).\nSaved to: {output_path}"
        )
        self._set_download_enabled(True)
        self.log_line(f"PDF downloaded from {url} -> {output_path}")

    def _on_download_error(self, message: str) -> None:
        self._set_status(f"Download failed: {message}")
        self._set_download_enabled(True)
        self.log_line(f"Download PDF failed: {message}")

    def _set_download_enabled(self, enabled: bool) -> None:
        self.download_button.enabled = enabled

    def _set_status(self, message: str) -> None:
        self.download_status_output.value = wrap_status_message(message)

    def _write_pdf(self, source_url: str, payload: bytes) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        filename = self._infer_filename(source_url)
        output_path = self.output_dir / filename

        if output_path.exists():
            stem = output_path.stem
            suffix = output_path.suffix or ".pdf"
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_path = self.output_dir / f"{stem}-{timestamp}{suffix}"

        output_path.write_bytes(payload)
        return output_path

    @staticmethod
    def _build_url(*, base_url: str, endpoint_path: str) -> str:
        if endpoint_path.lower().startswith(("http://", "https://")):
            return endpoint_path

        normalized_base = validate_base_url(base_url)
        normalized_endpoint = (
            endpoint_path if endpoint_path.startswith("/") else f"/{endpoint_path}"
        )
        return f"{normalized_base}{normalized_endpoint}"

    @staticmethod
    def _infer_filename(url: str) -> str:
        parsed = urlparse(url)
        candidate = Path(parsed.path).name.strip() or "downloaded.pdf"
        if not candidate.lower().endswith(".pdf"):
            return f"{candidate}.pdf"
        return candidate
