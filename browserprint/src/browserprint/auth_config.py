"""Persistent auth configuration and bearer token storage helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_DEFAULT_CONFIG_DIR = Path.home() / ".browserprint"
_DEFAULT_CONFIG_FILE = "auth_config.json"


def _load_keyring_module():
    try:
        import keyring
    except Exception:
        return None
    return keyring


@dataclass(slots=True)
class AuthConfig:
    api_base_url: str = "http://localhost"
    email: str = ""
    device_name: str = "browserprint"
    replace_existing: bool = False
    token_present: bool = False
    token_last_updated: str | None = None
    token_storage: str = "none"
    token_value: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> AuthConfig:
        return cls(
            api_base_url=str(payload.get("api_base_url", "http://localhost")),
            email=str(payload.get("email", "")),
            device_name=str(payload.get("device_name", "browserprint")),
            replace_existing=bool(payload.get("replace_existing", False)),
            token_present=bool(payload.get("token_present", False)),
            token_last_updated=payload.get("token_last_updated"),
            token_storage=str(payload.get("token_storage", "none")),
            token_value=payload.get("token_value"),
        )


class AuthConfigStore:
    """Read and write auth settings and bearer tokens for BrowserPrint."""

    def __init__(
        self,
        config_dir: Path | None = None,
        config_filename: str = _DEFAULT_CONFIG_FILE,
        keyring_module: Any | None = None,
        keyring_service_name: str = "browserprint",
        keyring_account_name: str = "sanctum_token",
    ) -> None:
        self.config_dir = config_dir or _DEFAULT_CONFIG_DIR
        self.config_path = self.config_dir / config_filename
        self._keyring = (
            keyring_module if keyring_module is not None else _load_keyring_module()
        )
        self._keyring_service_name = keyring_service_name
        self._keyring_account_name = keyring_account_name

    def load(self) -> AuthConfig:
        if not self.config_path.exists():
            return AuthConfig()

        try:
            payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return AuthConfig()

        if not isinstance(payload, dict):
            return AuthConfig()

        return AuthConfig.from_dict(payload)

    def save(self, config: AuthConfig) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(asdict(config), indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def get_token(self) -> str | None:
        config = self.load()

        if config.token_storage == "keyring" and self._keyring is not None:
            try:
                return self._keyring.get_password(
                    self._keyring_service_name,
                    self._keyring_account_name,
                )
            except Exception:
                return None

        if config.token_storage == "config":
            return config.token_value

        return None

    def set_token(self, token: str) -> None:
        config = self.load()
        timestamp = datetime.now(UTC).isoformat()

        if self._keyring is not None:
            try:
                self._keyring.set_password(
                    self._keyring_service_name,
                    self._keyring_account_name,
                    token,
                )
                config.token_storage = "keyring"
                config.token_value = None
                config.token_present = True
                config.token_last_updated = timestamp
                self.save(config)
                return
            except Exception:
                pass

        config.token_storage = "config"
        config.token_value = token
        config.token_present = True
        config.token_last_updated = timestamp
        self.save(config)

    def clear_token(self) -> None:
        config = self.load()

        if self._keyring is not None:
            try:
                self._keyring.delete_password(
                    self._keyring_service_name,
                    self._keyring_account_name,
                )
            except Exception:
                pass

        config.token_storage = "none"
        config.token_value = None
        config.token_present = False
        config.token_last_updated = datetime.now(UTC).isoformat()
        self.save(config)
