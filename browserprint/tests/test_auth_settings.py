import pytest
from browserprint.auth_utils import validate_base_url, wrap_status_message


def test_validate_base_url_accepts_http_and_trims_slash() -> None:
    assert validate_base_url("http://localhost/") == "http://localhost"
    assert validate_base_url("https://example.com/api/") == "https://example.com/api"


def test_validate_base_url_rejects_invalid_url() -> None:
    with pytest.raises(ValueError):
        validate_base_url("localhost")

    with pytest.raises(ValueError):
        validate_base_url("ftp://example.com")


def test_wrap_message_adds_breaklines() -> None:
    message = "This is a very long status message that should be wrapped into multiple lines to avoid growing the window unexpectedly."

    wrapped = wrap_status_message(message, width=30)

    assert "\n" in wrapped
    assert "unexpectedly." in wrapped
