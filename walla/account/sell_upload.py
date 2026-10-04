"""Multipart picture upload for Vender (/api/v3/upload/{id}/pictures)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from curl_cffi import CurlMime, requests

from walla.account.sell_steps import auth_headers
from walla.core.exceptions import WallaHTTPError
from walla.http.headers import API_BASE
from walla.http.polite import wait_turn

__all__ = ("IMAGE_TYPES", "upload_pictures")

IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def upload_pictures(upload_id: str, photos: list[Path]) -> int:
    """POST each photo to /api/v3/upload/{id}/pictures (HTTP 204)."""
    if not photos:
        raise ValueError("at least one photo required")
    headers = {k: v for k, v in auth_headers().items() if k.lower() != "content-type"}
    session: Any = requests.Session()
    for path in photos:
        data = path.read_bytes()
        ctype = IMAGE_TYPES.get(path.suffix.lower(), "image/jpeg")
        wait_turn()
        mp = CurlMime()
        mp.addpart(name="file", content_type=ctype, filename=path.name, data=data)
        resp: Any = session.request(
            "POST",
            f"{API_BASE}/api/v3/upload/{upload_id}/pictures",
            headers=headers,
            multipart=mp,
            impersonate="chrome",
            timeout=60,
        )
        mp.close()
        if resp.status_code not in (200, 201, 204):
            raise WallaHTTPError(
                f"picture upload HTTP {resp.status_code}: {(resp.text or '')[:200]}",
                status_code=resp.status_code,
            )
    return len(photos)
