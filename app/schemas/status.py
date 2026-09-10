"""Wire shapes for the JSON API."""

from pydantic import BaseModel


class Status(BaseModel):
    app: str
    python: str
    uptime_seconds: float
