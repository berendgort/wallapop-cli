"""Default browser-like headers for api.wallapop.com."""

from __future__ import annotations

import uuid

__all__ = (
    "API_BASE",
    "WEB_BASE",
    "default_headers",
    "new_device_id",
)

API_BASE = "https://api.wallapop.com"
WEB_BASE = "https://es.wallapop.com"


def new_device_id() -> str:
    return str(uuid.uuid4())


def default_headers(*, device_id: str | None = None) -> dict[str, str]:
    did = device_id or new_device_id()
    return {
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Origin": WEB_BASE,
        "Referer": f"{WEB_BASE}/",
        "X-DeviceOS": "0",
        "DeviceOS": "0",
        "X-DeviceID": did,
        "DeviceID": did,
    }
