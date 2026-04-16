"""Centralized environment-backed settings for BrowserPrint."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ENV_PATH = _PROJECT_ROOT / ".env"


def _load_environment() -> None:
    env_file_override = os.getenv("BROWSERPRINT_ENV_FILE", "").strip()
    if env_file_override:
        load_dotenv(env_file_override, override=False)
        return

    if _DEFAULT_ENV_PATH.exists():
        load_dotenv(_DEFAULT_ENV_PATH, override=False)
        return

    load_dotenv(override=False)


def _get_env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip()
    return normalized or default


def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip()
    if not normalized:
        return default

    try:
        return int(normalized)
    except ValueError:
        return default


def _get_env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if value is None:
        return default

    normalized = value.strip()
    if not normalized:
        return default

    candidate = Path(normalized).expanduser()
    if candidate.is_absolute():
        return candidate
    return (_PROJECT_ROOT / candidate).resolve()


def _get_env_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return list(default)

    parsed = [item.strip() for item in value.split(",") if item.strip()]
    if not parsed:
        return list(default)
    return parsed


_load_environment()

DEFAULT_CONFIG_DIR = _get_env_path(
    "BROWSERPRINT_CONFIG_DIR", Path.home() / ".browserprint"
)
DEFAULT_CONFIG_FILE = _get_env_str("BROWSERPRINT_CONFIG_FILE", "auth_config.json")
DEFAULT_API_BASE_URL = _get_env_str(
    "BROWSERPRINT_DEFAULT_API_BASE_URL", "http://localhost"
)

LOCAL_API_HOST = _get_env_str("BROWSERPRINT_LOCAL_API_HOST", "127.0.0.1")
LOCAL_API_PORT = _get_env_int("BROWSERPRINT_LOCAL_API_PORT", 8003)

DEFAULT_ALLOWED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8003",
    "http://127.0.0.1",
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:8003",
]
ALLOWED_ORIGINS = _get_env_list("BROWSERPRINT_ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS)

DEBUG_OUTPUT_DIR = _get_env_path(
    "BROWSERPRINT_DEBUG_OUTPUT_DIR",
    Path.home() / "Desktop" / "debug_pdfs",
)

SUMATRA_PATH = _get_env_path(
    "BROWSERPRINT_SUMATRA_PATH",
    Path(__file__).resolve().parent
    / "resources"
    / "vendor"
    / "sumatrapdf"
    / "SumatraPDF-3.6-64.exe",
)

SANCTUM_TIMEOUT_SECONDS = _get_env_int("BROWSERPRINT_SANCTUM_TIMEOUT_SECONDS", 15)
MANUAL_REQUEST_TIMEOUT_SECONDS = _get_env_int(
    "BROWSERPRINT_MANUAL_REQUEST_TIMEOUT_SECONDS", 20
)

DOWNLOAD_TIMEOUT_SECONDS = _get_env_int("BROWSERPRINT_DOWNLOAD_TIMEOUT_SECONDS", 20)
MAX_PDF_BYTES = _get_env_int("BROWSERPRINT_MAX_PDF_BYTES", 10 * 1024 * 1024)
LARAVEL_AUTH_HEADER = _get_env_str("BROWSERPRINT_LARAVEL_AUTH_HEADER", "Authorization")
