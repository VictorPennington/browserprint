"""HTTP client for BrowserPrint token lifecycle against Laravel Sanctum endpoints."""

from __future__ import annotations

from dataclasses import dataclass

import requests

_DEFAULT_TIMEOUT_SECONDS = 15


@dataclass(slots=True)
class PingResult:
    ok: bool
    status_code: int
    message: str


class SanctumClientError(RuntimeError):
    """Raised when Sanctum operations fail or return unexpected responses."""


class SanctumClient:
    def __init__(self, timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS) -> None:
        self.timeout_seconds = timeout_seconds

    def generate_token(
        self,
        *,
        base_url: str,
        email: str,
        password: str,
        device_name: str,
        replace_existing: bool,
    ) -> str:
        response = self._request(
            method="POST",
            url=self._endpoint(base_url, "/api/browserprint/token"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={
                "email": email,
                "password": password,
                "device_name": device_name,
                "replace_existing": replace_existing,
            },
        )

        if response.status_code >= 400:
            raise SanctumClientError(
                f"Token generation failed ({response.status_code}): {self._error_message(response)}"
            )

        payload = self._json_or_empty(response)
        token = (
            str(payload.get("token", "")).strip()
            or str(payload.get("access_token", "")).strip()
        )
        if not token:
            raise SanctumClientError(
                "Token generation succeeded but no token was returned"
            )

        return token

    def ping(self, *, base_url: str, token: str) -> PingResult:
        response = self._request(
            method="GET",
            url=self._endpoint(base_url, "/api/browserprint/ping"),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )

        payload = self._json_or_empty(response)
        message = str(payload.get("message", "")).strip() or response.reason
        return PingResult(
            ok=response.status_code < 400,
            status_code=response.status_code,
            message=message,
        )

    def revoke_token(self, *, base_url: str, token: str) -> None:
        response = self._request(
            method="POST",
            url=self._endpoint(base_url, "/api/browserprint/token/revoke"),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
            },
        )

        if response.status_code >= 400:
            raise SanctumClientError(
                f"Token revoke failed ({response.status_code}): {self._error_message(response)}"
            )

    def _request(self, *, method: str, url: str, headers: dict[str, str], json=None):
        try:
            return requests.request(
                method=method,
                url=url,
                headers=headers,
                json=json,
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise SanctumClientError("Request to eDiary API timed out") from exc
        except requests.RequestException as exc:
            raise SanctumClientError(f"Request to eDiary API failed: {exc}") from exc

    @staticmethod
    def _endpoint(base_url: str, path: str) -> str:
        return f"{base_url.rstrip('/')}{path}"

    @staticmethod
    def _json_or_empty(response) -> dict:
        try:
            payload = response.json()
        except ValueError:
            return {}
        if isinstance(payload, dict):
            return payload
        return {}

    def _error_message(self, response) -> str:
        payload = self._json_or_empty(response)

        for key in ("message", "error", "detail"):
            value = payload.get(key)
            if value:
                return str(value)

        return response.text.strip() or response.reason
