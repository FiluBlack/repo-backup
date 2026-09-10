"""Application settings.

Values come from the environment, falling back to a .env file, then to the
defaults below. Field names map to environment variables case-insensitively,
so `app_name` is read from APP_NAME.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "repo-backup"
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True
