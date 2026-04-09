from types import SimpleNamespace

from browserprint.api.manual_request_client import (
    ManualRequestClientError,
    ManualRequestResult,
)
from browserprint.auth_config import AuthConfig
from browserprint.ui.make_request import MakeRequestController


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


class FakeRequestClient:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.last_call = None

    def send(self, **kwargs):
        self.last_call = kwargs
        if self.error is not None:
            raise self.error
        return self.result


def make_controller(store: FakeAuthStore, request_client: FakeRequestClient):
    logs: list[str] = []
    controller = MakeRequestController(
        app=FakeApp(),
        log_line=logs.append,
        auth_store=store,
        request_client=request_client,
    )
    controller.base_url_value = SimpleNamespace(text="")
    controller.endpoint_input = SimpleNamespace(value="/api/custom")
    controller.method_input = SimpleNamespace(value="POST")
    controller.payload_input = SimpleNamespace(value='{"id": 10}')
    controller.send_button = SimpleNamespace(enabled=True)
    controller.request_status_output = SimpleNamespace(value="")
    return controller, logs


def test_refresh_values_displays_base_url_and_token_state() -> None:
    store = FakeAuthStore(
        AuthConfig(
            api_base_url="http://localhost:8000",
            token_present=True,
            token_storage="config",
        ),
        token="1|TokenValue",
    )
    controller, _ = make_controller(store, FakeRequestClient())

    controller._refresh_values()

    assert controller.base_url_value.text == "http://localhost:8000"
    assert "Token present=True" in controller.request_status_output.value


def test_send_request_requires_stored_token() -> None:
    store = FakeAuthStore(
        AuthConfig(api_base_url="http://localhost", token_present=False),
        token=None,
    )
    request_client = FakeRequestClient()
    controller, logs = make_controller(store, request_client)

    controller._send_request()

    assert "No token available" in controller.request_status_output.value
    assert "no stored token" in logs[0].lower()
    assert request_client.last_call is None


def test_send_request_worker_reports_success() -> None:
    store = FakeAuthStore(
        AuthConfig(api_base_url="http://localhost:8000", token_present=True),
        token="1|TokenValue",
    )
    request_client = FakeRequestClient(
        result=ManualRequestResult(
            ok=True,
            status_code=200,
            method="POST",
            url="http://localhost:8000/api/custom",
            body_preview='{"ok": true}',
        )
    )
    controller, logs = make_controller(store, request_client)
    controller.send_button.enabled = False

    controller._send_request_worker("POST", "/api/custom", '{"id": 10}', "token")

    assert "Request succeeded with status 200" in controller.request_status_output.value
    assert controller.send_button.enabled is True
    assert "Manual request POST http://localhost:8000/api/custom -> 200" in logs[0]


def test_send_request_worker_reports_client_errors() -> None:
    store = FakeAuthStore(
        AuthConfig(api_base_url="http://localhost:8000", token_present=True),
        token="1|TokenValue",
    )
    request_client = FakeRequestClient(
        error=ManualRequestClientError("Payload must be valid JSON")
    )
    controller, logs = make_controller(store, request_client)
    controller.send_button.enabled = False

    controller._send_request_worker("POST", "/api/custom", "{bad}", "token")

    assert "Request failed" in controller.request_status_output.value
    assert "valid JSON" in controller.request_status_output.value
    assert controller.send_button.enabled is True
    assert "manual request failed" in logs[0].lower()
