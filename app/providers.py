"""Providers: objects FastAPI injects into route functions."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.settings import Settings


@lru_cache
def get_settings() -> Settings:
    """Settings are read once and reused for the process lifetime."""
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
