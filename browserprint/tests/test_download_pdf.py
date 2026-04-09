from pathlib import Path
from types import SimpleNamespace

from browserprint.api.pdf_fetcher import PDFDownloadError
from browserprint.auth_config import AuthConfig
from browserprint.ui.download_pdf import DownloadPdfController


class FakeLoop:
    def call_soon_threadsafe(self, callback, *args):
        callback(*args)


class FakeApp:
    def __init__(self) -> None:
        self.loop = FakeLoop()


class FakeAuthStore:
    def __init__(self, config: AuthConfig, token: str | None) -> None:
        self._config = config
        self._token = token

    def load(self) -> AuthConfig:
        return self._config

    def get_token(self) -> str | None:
        return self._token


class FakePdfFetcher:
    def __init__(self, payload: bytes | None = None, error: Exception | None = None):
        self.payload = payload or b"%PDF-test"
        self.error = error
        self.last_call = None

    def __call__(self, url: str, token: str | None):
        self.last_call = {"url": url, "token": token}
        if self.error is not None:
            raise self.error
        return self.payload


def make_controller(
    store: FakeAuthStore,
    pdf_fetcher: FakePdfFetcher,
    output_dir: Path,
):
    logs: list[str] = []
    controller = DownloadPdfController(
        app=FakeApp(),
        log_line=logs.append,
        auth_store=store,
        pdf_fetcher=pdf_fetcher,
        output_dir=output_dir,
    )
    controller.base_url_value = SimpleNamespace(text="")
    controller.endpoint_input = SimpleNamespace(value="/api/docs/test")
    controller.download_button = SimpleNamespace(enabled=True)
    controller.download_status_output = SimpleNamespace(value="")
    return controller, logs


def test_refresh_values_displays_base_url_and_token_state(tmp_path: Path) -> None:
    store = FakeAuthStore(
        AuthConfig(
            api_base_url="http://localhost:8000",
            token_present=True,
            token_storage="config",
        ),
        token="1|TokenValue",
    )
    controller, _ = make_controller(store, FakePdfFetcher(), tmp_path)

    controller._refresh_values()

    assert controller.base_url_value.text == "http://localhost:8000"
    assert "Token present=True" in controller.download_status_output.value


def test_download_requires_stored_token(tmp_path: Path) -> None:
    store = FakeAuthStore(
        AuthConfig(api_base_url="http://localhost", token_present=False),
        token=None,
    )
    fetcher = FakePdfFetcher()
    controller, logs = make_controller(store, fetcher, tmp_path)

    controller._download_pdf()

    assert "No token available" in controller.download_status_output.value
    assert "no stored token" in logs[0].lower()
    assert fetcher.last_call is None


def test_download_requires_endpoint(tmp_path: Path) -> None:
    store = FakeAuthStore(
        AuthConfig(api_base_url="http://localhost:8000", token_present=True),
        token="1|TokenValue",
    )
    fetcher = FakePdfFetcher()
    controller, logs = make_controller(store, fetcher, tmp_path)
    controller.endpoint_input.value = ""

    controller._download_pdf()

    assert "endpoint is required" in controller.download_status_output.value.lower()
    assert "endpoint is empty" in logs[0].lower()
    assert fetcher.last_call is None


def test_download_worker_reports_success(tmp_path: Path) -> None:
    store = FakeAuthStore(
        AuthConfig(api_base_url="http://localhost:8000", token_present=True),
        token="1|TokenValue",
    )
    fetcher = FakePdfFetcher(payload=b"%PDF-success")
    controller, logs = make_controller(store, fetcher, tmp_path)
    controller.download_button.enabled = False

    controller._download_worker("http://localhost:8000/files/invoice.pdf", "token")

    assert "Download completed" in controller.download_status_output.value
    assert controller.download_button.enabled is True
    assert fetcher.last_call == {
        "url": "http://localhost:8000/files/invoice.pdf",
        "token": "token",
    }
    assert "pdf downloaded" in logs[0].lower()
    saved_files = list(tmp_path.glob("invoice*.pdf"))
    assert saved_files


def test_download_worker_reports_pdf_errors(tmp_path: Path) -> None:
    store = FakeAuthStore(
        AuthConfig(api_base_url="http://localhost:8000", token_present=True),
        token="1|TokenValue",
    )
    fetcher = FakePdfFetcher(error=PDFDownloadError("auth failed"))
    controller, logs = make_controller(store, fetcher, tmp_path)
    controller.download_button.enabled = False

    controller._download_worker("http://localhost:8000/files/invoice.pdf", "token")

    assert "Download failed" in controller.download_status_output.value
    assert "auth failed" in controller.download_status_output.value
    assert controller.download_button.enabled is True
    assert "download pdf failed" in logs[0].lower()
