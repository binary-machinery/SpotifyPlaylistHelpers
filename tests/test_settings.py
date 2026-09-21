import pytest
from pydantic import ValidationError

from sph_backend.settings import Settings


@pytest.fixture
def clear_settings(monkeypatch):
    monkeypatch.delenv("SERVER_HOST", raising=False)
    monkeypatch.delenv("SERVER_SECRET", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_ID", raising=False)
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("USERS_DB", raising=False)


@pytest.fixture
def set_settings(monkeypatch):
    monkeypatch.setenv("SERVER_HOST", "http://127.0.0.1:8000")
    monkeypatch.setenv("SERVER_SECRET", "server_secret_value")
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "spotify_client_id_value")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "spotify_client_secret_value")
    monkeypatch.setenv("USERS_DB", "users_db_value")


def test_fails_if_missing_settings(clear_settings):
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_load_from_env_vars(set_settings):
    settings = Settings(_env_file=None)

    assert settings.server_host == "http://127.0.0.1:8000"
    assert settings.server_secret.get_secret_value() == "server_secret_value"
    assert settings.spotify_client_id == "spotify_client_id_value"
    assert settings.spotify_client_secret.get_secret_value() == "spotify_client_secret_value"


def test_settings_hide_secrets(set_settings):
    settings = Settings(_env_file=None)

    assert "server_secret_value" not in str(settings)
    assert "spotify_client_secret_value" not in str(settings)
