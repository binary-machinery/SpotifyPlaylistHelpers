from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    server_host: str
    server_secret: SecretStr
    spotify_client_id: str
    spotify_client_secret: SecretStr
    users_db_path: str = "users.sqlite"


@lru_cache
def get_settings() -> Settings:
    # noinspection PyArgumentList
    return Settings()
