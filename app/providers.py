"""Providers: objects FastAPI injects into route functions."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.settings import Settings


# This function is needed to avoid creating a new Settings instance for every request,
# else if Depends(Settings) is used directly, it will create a new instance for every request.
@lru_cache
def get_settings() -> Settings:
    """Settings are read once and reused for the process lifetime."""
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
