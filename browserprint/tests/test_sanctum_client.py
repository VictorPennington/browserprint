import pytest
import requests
from browserprint.api.sanctum_client import (
    PingResult,
    SanctumClient,
    SanctumClientError,
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


def test_generate_token_returns_token(monkeypatch) -> None:
    client = SanctumClient()

    def fake_request(method, url, headers, json, timeout):
        assert method == "POST"
        assert url == "http://localhost/api/browserprint/token"
        assert json["email"] == "user@example.com"
        return DummyResponse(status_code=200, payload={"token": "1|AbCdEf123"})

    monkeypatch.setattr(
        "browserprint.api.sanctum_client.requests.request", fake_request
    )

    token = client.generate_token(
        base_url="http://localhost",
        email="user@example.com",
        password="secret",
        device_name="browserprint",
        replace_existing=False,
    )

    assert token == "1|AbCdEf123"


def test_generate_token_raises_on_error(monkeypatch) -> None:
    client = SanctumClient()

    def fake_request(method, url, headers, json, timeout):
        return DummyResponse(
            status_code=422,
            payload={"message": "The provided credentials are incorrect."},
        )

    monkeypatch.setattr(
        "browserprint.api.sanctum_client.requests.request", fake_request
    )

    with pytest.raises(SanctumClientError) as exc_info:
        client.generate_token(
            base_url="http://localhost",
            email="user@example.com",
            password="bad",
            device_name="browserprint",
            replace_existing=False,
        )

    assert "credentials" in str(exc_info.value).lower()


def test_ping_returns_result(monkeypatch) -> None:
    client = SanctumClient()

    def fake_request(method, url, headers, json, timeout):
        assert method == "GET"
        return DummyResponse(status_code=200, payload={"message": "pong"})

    monkeypatch.setattr(
        "browserprint.api.sanctum_client.requests.request", fake_request
    )

    result = client.ping(base_url="http://localhost", token="1|AbCdEf123")

    assert isinstance(result, PingResult)
    assert result.ok is True
    assert result.status_code == 200
    assert result.message == "pong"


def test_revoke_token_raises_on_error(monkeypatch) -> None:
    client = SanctumClient()

    def fake_request(method, url, headers, json, timeout):
        return DummyResponse(status_code=401, payload={"message": "Unauthenticated."})

    monkeypatch.setattr(
        "browserprint.api.sanctum_client.requests.request", fake_request
    )

    with pytest.raises(SanctumClientError) as exc_info:
        client.revoke_token(base_url="http://localhost", token="invalid")

    assert "revoke" in str(exc_info.value).lower()


def test_request_timeout_maps_to_sanctum_error(monkeypatch) -> None:
    client = SanctumClient(timeout_seconds=1)

    def fake_request(method, url, headers, json, timeout):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(
        "browserprint.api.sanctum_client.requests.request", fake_request
    )

    with pytest.raises(SanctumClientError) as exc_info:
        client.ping(base_url="http://localhost", token="1|AbCdEf123")

    assert "timed out" in str(exc_info.value).lower()
