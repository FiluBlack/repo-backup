"""Runtime facts about the running process.

Imports nothing from FastAPI: callable from a router, a test, or a script.
"""

import platform
import time
from typing import TypedDict

_STARTED = time.monotonic()


def uptime_seconds() -> float:
    return time.monotonic() - _STARTED


class StatusData(TypedDict):
    """The shape collect() returns, so callers can be type-checked."""

    app: str
    python: str
    uptime_seconds: float


def collect(app_name: str) -> StatusData:
    return {
        "app": app_name,
        "python": platform.python_version(),
        "uptime_seconds": round(uptime_seconds(), 1),
    }
