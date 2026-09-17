from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    server_host: str = None
    server_secret: SecretStr = None
    spotify_client_id: str = None
    spotify_client_secret: SecretStr = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
