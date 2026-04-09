import pytest
from browserprint.api.manual_request_client import (
    ManualRequestClient,
    ManualRequestClientError,
)


class DummyResponse:
    def __init__(
        self,
        *,
        status_code: int,
        payload: dict | None = None,
        text: str = "",
        reason: str = "OK",
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.reason = reason

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def test_send_uses_bearer_token_and_relative_endpoint(monkeypatch) -> None:
    client = ManualRequestClient()
    captured = {}

    def fake_request(method, url, headers, timeout, json):
        captured["method"] = method
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return DummyResponse(status_code=201, payload={"ok": True})

    monkeypatch.setattr(
        "browserprint.api.manual_request_client.requests.request", fake_request
    )

    result = client.send(
        base_url="http://localhost:8080",
        token="1|TokenValue",
        endpoint_path="api/test",
        method="post",
        payload_text='{"name": "demo"}',
    )

    assert result.ok is True
    assert result.status_code == 201
    assert result.url == "http://localhost:8080/api/test"
    assert captured["method"] == "POST"
    assert captured["headers"]["Authorization"] == "Bearer 1|TokenValue"
    assert captured["json"] == {"name": "demo"}


def test_send_accepts_full_url_without_base_join(monkeypatch) -> None:
    client = ManualRequestClient()

    def fake_request(method, url, headers, timeout):
        assert method == "GET"
        assert url == "https://api.example.com/custom/ping"
        return DummyResponse(status_code=200, payload={"message": "pong"})

    monkeypatch.setattr(
        "browserprint.api.manual_request_client.requests.request", fake_request
    )

    result = client.send(
        base_url="http://ignored.local",
        token="1|TokenValue",
        endpoint_path="https://api.example.com/custom/ping",
        method="GET",
        payload_text="",
    )

    assert result.ok is True
    assert "pong" in result.body_preview


def test_send_rejects_invalid_http_method() -> None:
    client = ManualRequestClient()

    with pytest.raises(ManualRequestClientError) as exc_info:
        client.send(
            base_url="http://localhost",
            token="1|TokenValue",
            endpoint_path="/api/test",
            method="TRACE",
            payload_text="{}",
        )

    assert "invalid http method" in str(exc_info.value).lower()


def test_send_rejects_invalid_json_payload() -> None:
    client = ManualRequestClient()

    with pytest.raises(ManualRequestClientError) as exc_info:
        client.send(
            base_url="http://localhost",
            token="1|TokenValue",
            endpoint_path="/api/test",
            method="POST",
            payload_text="{invalid}",
        )

    assert "valid json" in str(exc_info.value).lower()
