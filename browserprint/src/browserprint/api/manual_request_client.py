"""HTTP client for custom authenticated request testing from the desktop UI."""

from __future__ import annotations

import json
from dataclasses import dataclass

import requests

from browserprint.auth_utils import validate_base_url

_DEFAULT_TIMEOUT_SECONDS = 20
_MAX_BODY_PREVIEW_CHARS = 1200
_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


@dataclass(slots=True)
class ManualRequestResult:
    ok: bool
    status_code: int
    method: str
    url: str
    body_preview: str


class ManualRequestClientError(RuntimeError):
    """Raised when custom request validation or execution fails."""


class ManualRequestClient:
    def __init__(self, timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS) -> None:
        self.timeout_seconds = timeout_seconds

    def send(
        self,
        *,
        base_url: str,
        token: str,
        endpoint_path: str,
        method: str,
        payload_text: str,
    ) -> ManualRequestResult:
        normalized_method = method.strip().upper()
        if normalized_method not in _ALLOWED_METHODS:
            raise ManualRequestClientError(
                "Invalid HTTP method. Use one of: GET, POST, PUT, PATCH, DELETE"
            )

        cleaned_endpoint = endpoint_path.strip()
        if not cleaned_endpoint:
            raise ManualRequestClientError("Endpoint path is required")

        url = self._build_url(base_url=base_url, endpoint_path=cleaned_endpoint)
        payload = self._parse_payload(payload_text)

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        request_kwargs: dict = {}
        if payload is not None:
            headers["Content-Type"] = "application/json"
            request_kwargs["json"] = payload

        response = self._request(
            method=normalized_method,
            url=url,
            headers=headers,
            **request_kwargs,
        )

        return ManualRequestResult(
            ok=response.status_code < 400,
            status_code=response.status_code,
            method=normalized_method,
            url=url,
            body_preview=self._response_preview(response),
        )

    def _request(self, *, method: str, url: str, headers: dict[str, str], **kwargs):
        try:
            return requests.request(
                method=method,
                url=url,
                headers=headers,
                timeout=self.timeout_seconds,
                **kwargs,
            )
        except requests.Timeout as exc:
            raise ManualRequestClientError("Request timed out") from exc
        except requests.RequestException as exc:
            raise ManualRequestClientError(f"Request failed: {exc}") from exc

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
    def _parse_payload(payload_text: str):
        stripped = payload_text.strip()
        if not stripped:
            return None

        try:
            return json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ManualRequestClientError(
                f"Payload must be valid JSON: {exc.msg}"
            ) from exc

    @staticmethod
    def _response_preview(response) -> str:
        try:
            payload = response.json()
            text = json.dumps(payload, indent=2, ensure_ascii=True)
        except ValueError:
            text = response.text.strip() or response.reason

        if len(text) > _MAX_BODY_PREVIEW_CHARS:
            return f"{text[:_MAX_BODY_PREVIEW_CHARS]}\n...(truncated)"
        return text
