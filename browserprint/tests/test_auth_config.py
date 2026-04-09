from browserprint.auth_config import AuthConfig, AuthConfigStore


class FakeKeyring:
    def __init__(self):
        self._values = {}

    def set_password(self, service_name: str, account_name: str, token: str) -> None:
        self._values[(service_name, account_name)] = token

    def get_password(self, service_name: str, account_name: str):
        return self._values.get((service_name, account_name))

    def delete_password(self, service_name: str, account_name: str) -> None:
        self._values.pop((service_name, account_name), None)


class FailingKeyring:
    def set_password(self, service_name: str, account_name: str, token: str) -> None:
        raise RuntimeError("keyring backend unavailable")

    def get_password(self, service_name: str, account_name: str):
        raise RuntimeError("keyring backend unavailable")

    def delete_password(self, service_name: str, account_name: str) -> None:
        raise RuntimeError("keyring backend unavailable")


def test_load_returns_defaults_for_missing_file(tmp_path) -> None:
    store = AuthConfigStore(config_dir=tmp_path, keyring_module=None)

    config = store.load()

    assert config == AuthConfig()


def test_save_and_load_roundtrip(tmp_path) -> None:
    store = AuthConfigStore(config_dir=tmp_path, keyring_module=None)

    store.save(
        AuthConfig(
            api_base_url="http://localhost",
            email="user@example.com",
            device_name="browserprint-desktop",
            replace_existing=True,
            token_present=False,
        )
    )

    loaded = store.load()

    assert loaded.email == "user@example.com"
    assert loaded.device_name == "browserprint-desktop"
    assert loaded.replace_existing is True


def test_set_token_uses_keyring_when_available(tmp_path) -> None:
    keyring = FakeKeyring()
    store = AuthConfigStore(config_dir=tmp_path, keyring_module=keyring)

    store.set_token("1|AbCdEf123")

    config = store.load()
    assert config.token_storage == "keyring"
    assert config.token_present is True
    assert config.token_value is None
    assert store.get_token() == "1|AbCdEf123"


def test_set_token_falls_back_to_config_when_keyring_fails(tmp_path) -> None:
    store = AuthConfigStore(config_dir=tmp_path, keyring_module=FailingKeyring())

    store.set_token("1|AbCdEf123")

    config = store.load()
    assert config.token_storage == "config"
    assert config.token_present is True
    assert config.token_value == "1|AbCdEf123"
    assert store.get_token() == "1|AbCdEf123"


def test_clear_token_resets_metadata_and_value(tmp_path) -> None:
    keyring = FakeKeyring()
    store = AuthConfigStore(config_dir=tmp_path, keyring_module=keyring)

    store.set_token("1|AbCdEf123")
    store.clear_token()

    config = store.load()
    assert config.token_storage == "none"
    assert config.token_present is False
    assert config.token_value is None
    assert store.get_token() is None
