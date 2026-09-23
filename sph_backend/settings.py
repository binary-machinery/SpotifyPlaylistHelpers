from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="settings.env", extra="ignore")

    server_host: str
    server_secret: SecretStr
    auth_redirect_endpoint: str = "/auth-callback"
    spotify_client_id: str
    spotify_client_secret: SecretStr
    users_db_path: str = "users.sqlite"

    @property
    def auth_redirect_url(self):
        return self.server_host + self.auth_redirect_endpoint


@lru_cache
def get_settings() -> Settings:
    # noinspection PyArgumentList
    return Settings()
