"""Runtime facts about the running process.

Imports nothing from FastAPI: callable from a router, a test, or a script.
"""

import platform
import time

_STARTED = time.monotonic()


def uptime_seconds() -> float:
    return time.monotonic() - _STARTED


def collect(app_name: str) -> dict[str, object]:
    return {
        "app": app_name,
        "python": platform.python_version(),
        "uptime_seconds": round(uptime_seconds(), 1),
    }
