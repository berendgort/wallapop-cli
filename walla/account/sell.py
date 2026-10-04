"""Vender flow: steps → pictures → create item (upload-v2)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from curl_cffi import CurlMime, requests

from walla.account.login import ensure_access_token
from walla.account.sell_wire import build_item_body
from walla.core.exceptions import WallaHTTPError, WallaUnsupportedError
from walla.http.client import HttpClient
from walla.http.headers import API_BASE, default_headers
from walla.http.polite import wait_turn

__all__ = (
    "create_listing",
    "delete_listing",
    "publish_listing",
    "upload_pictures",
)

_UPLOAD_ACCEPT = "application/vnd.upload-v2+json"
_IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _auth_client() -> HttpClient:
    sess = ensure_access_token()
    return HttpClient(access_token=sess.access_token, device_id=sess.device_id)


def _auth_headers() -> dict[str, str]:
    sess = ensure_access_token()
    headers = default_headers(device_id=sess.device_id)
    headers["Authorization"] = f"Bearer {sess.access_token}"
    return headers


def _step(
    http: HttpClient,
    upload_id: str,
    *,
    current: str | None,
    draft: dict[str, Any],
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "mode": {"action": "upload", "id": upload_id},
        "draft": draft,
    }
    if current:
        body["current_step"] = current
    raw = http.post("/api/v3/steps", json_body=body, auth=True)
    if not isinstance(raw, dict):
        raise WallaUnsupportedError("steps returned non-object")
    return raw


def upload_pictures(upload_id: str, photos: list[Path]) -> int:
    """POST each photo to /api/v3/upload/{id}/pictures (HTTP 204)."""
    if not photos:
        raise ValueError("at least one photo required")
    headers = {k: v for k, v in _auth_headers().items() if k.lower() != "content-type"}
    session: Any = requests.Session()
    for path in photos:
        data = path.read_bytes()
        ctype = _IMAGE_TYPES.get(path.suffix.lower(), "image/jpeg")
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


def create_listing(item: dict[str, Any], first_photo: Path) -> dict[str, Any]:
    """Multipart POST /api/v3/items with Accept upload-v2."""
    headers = {k: v for k, v in _auth_headers().items() if k.lower() != "content-type"}
    headers["Accept"] = _UPLOAD_ACCEPT
    data = first_photo.read_bytes()
    ctype = _IMAGE_TYPES.get(first_photo.suffix.lower(), "image/jpeg")
    wait_turn()
    mp = CurlMime()
    mp.addpart(name="image", content_type=ctype, filename=first_photo.name, data=data)
    mp.addpart(name="item", data=json.dumps(item).encode("utf-8"))
    resp: Any = requests.Session().request(
        "POST",
        f"{API_BASE}/api/v3/items",
        headers=headers,
        multipart=mp,
        impersonate="chrome",
        timeout=60,
    )
    mp.close()
    if resp.status_code not in (200, 201):
        raise WallaHTTPError(
            f"create item HTTP {resp.status_code}: {(resp.text or '')[:300]}",
            status_code=resp.status_code,
        )
    raw = resp.json()
    if not isinstance(raw, dict) or not raw.get("id"):
        raise WallaUnsupportedError(f"create item missing id: {raw!r}"[:200])
    return {"id": str(raw["id"]), "flags": raw.get("flags") or {}}


def delete_listing(item_id: str, *, client: HttpClient | None = None) -> dict[str, Any]:
    http = client or _auth_client()
    http.delete(f"/api/v3/items/{item_id}", auth=True)
    return {"id": item_id, "deleted": True}


def publish_listing(
    photos: list[Path],
    *,
    title: str,
    description: str,
    price_eur: float,
    category_leaf_id: str,
    root_category_id: str,
    lat: float,
    lon: float,
    condition: str = "good",
    shipping: bool = False,
    weight_kg: float | None = None,
) -> dict[str, Any]:
    """Full Vender path. Caller must already require --yes."""
    paths = [Path(p) for p in photos]
    for p in paths:
        if not p.is_file():
            raise ValueError(f"photo not found: {p}")
    http = _auth_client()
    upload_id = str(uuid.uuid4())
    draft: dict[str, Any] = {"title": title.strip()[:50]}
    _step(http, upload_id, current=None, draft={})
    _step(http, upload_id, current="title", draft=draft)
    upload_pictures(upload_id, paths)
    _step(http, upload_id, current="photo", draft=draft)
    draft = {
        **draft,
        "category_leaf_id": str(category_leaf_id),
        "root_category_id": str(root_category_id),
    }
    _step(http, upload_id, current="category", draft=draft)
    for _ in range(8):
        wait_turn()
        try:
            http.get(f"/api/v3/suggested-item-data/{upload_id}", auth=True)
            break
        except WallaHTTPError as exc:
            if exc.status_code != 404:
                raise
    _step(http, upload_id, current="loading", draft=draft)
    item = build_item_body(
        upload_id=upload_id,
        title=title,
        description=description,
        price_eur=price_eur,
        category_leaf_id=category_leaf_id,
        lat=lat,
        lon=lon,
        condition=condition,
        shipping=shipping,
        max_weight_kg=weight_kg,
    )
    created = create_listing(item, paths[0])
    if len(paths) > 1:
        _upload_extra_pictures(created["id"], paths[1:])
    return {
        **created,
        "upload_id": upload_id,
        "title": title.strip()[:50],
        "url": f"https://es.wallapop.com/item/{created['id']}",
        "photos": len(paths),
    }


def _upload_extra_pictures(item_id: str, photos: list[Path]) -> None:
    headers = {k: v for k, v in _auth_headers().items() if k.lower() != "content-type"}
    headers["Accept"] = _UPLOAD_ACCEPT
    session: Any = requests.Session()
    for idx, path in enumerate(photos, start=1):
        data = path.read_bytes()
        ctype = _IMAGE_TYPES.get(path.suffix.lower(), "image/jpeg")
        wait_turn()
        mp = CurlMime()
        mp.addpart(name="image", content_type=ctype, filename=path.name, data=data)
        mp.addpart(name="order", data=str(idx).encode("utf-8"))
        resp: Any = session.request(
            "POST",
            f"{API_BASE}/api/v3/items/{item_id}/picture2",
            headers=headers,
            multipart=mp,
            impersonate="chrome",
            timeout=60,
        )
        mp.close()
        if resp.status_code not in (200, 201, 204):
            raise WallaHTTPError(
                f"picture2 HTTP {resp.status_code}: {(resp.text or '')[:200]}",
                status_code=resp.status_code,
            )
