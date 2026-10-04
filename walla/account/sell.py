"""Vender flow: steps → pictures → create item (upload-v2)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from curl_cffi import CurlMime, requests

from walla.account.sell_steps import (
    auth_client,
    auth_headers,
    parse_steps_draft,
    poll_suggested,
    post_step,
)
from walla.account.sell_upload import IMAGE_TYPES, upload_pictures
from walla.account.sell_wire import build_item_body
from walla.core.exceptions import (
    WallaHTTPError,
    WallaNotFoundError,
    WallaParseError,
    WallaUnsupportedError,
)
from walla.http.client import HttpClient
from walla.http.headers import API_BASE, WEB_BASE
from walla.http.polite import wait_turn
from walla.search.api import get_item
from walla.search.parse import item_url

__all__ = (
    "create_listing",
    "delete_listing",
    "publish_listing",
    "publish_prepared",
    "upload_pictures",
)

_UPLOAD_ACCEPT = "application/vnd.upload-v2+json"


def create_listing(item: dict[str, Any], first_photo: Path) -> dict[str, Any]:
    """Multipart POST /api/v3/items with Accept upload-v2."""
    headers = {k: v for k, v in auth_headers().items() if k.lower() != "content-type"}
    headers["Accept"] = _UPLOAD_ACCEPT
    data = first_photo.read_bytes()
    ctype = IMAGE_TYPES.get(first_photo.suffix.lower(), "image/jpeg")
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
    http = client or auth_client()
    http.delete(f"/api/v3/items/{item_id}", auth=True)
    return {"id": item_id, "deleted": True}


def publish_prepared(
    photos: list[Path],
    *,
    upload_id: str,
    title: str,
    description: str,
    price_eur: float,
    category_leaf_id: str,
    lat: float,
    lon: float,
    condition: str = "good",
    shipping: bool = False,
    weight_kg: float | None = None,
    wire_draft: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create item from an upload_id already walked through loading."""
    paths = [Path(p) for p in photos]
    for p in paths:
        if not p.is_file():
            raise ValueError(f"photo not found: {p}")
    if not upload_id.strip():
        raise ValueError("upload_id required")
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
        "url": _public_item_url(str(created["id"])),
        "photos": len(paths),
        "wire_draft": wire_draft or {},
        "reused_suggest": True,
    }


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
    http = auth_client()
    upload_id = str(uuid.uuid4())
    draft: dict[str, Any] = {"title": title.strip()[:50]}
    post_step(http, upload_id, current=None, draft={})
    post_step(http, upload_id, current="title", draft=draft)
    upload_pictures(upload_id, paths)
    after_photo = post_step(http, upload_id, current="photo", draft=draft)
    wire = parse_steps_draft(after_photo)
    leaf = str(category_leaf_id)
    root = str(root_category_id)
    draft = {**draft, "category_leaf_id": leaf, "root_category_id": root}
    post_step(http, upload_id, current="category", draft=draft)
    poll_suggested(http, upload_id)
    post_step(http, upload_id, current="loading", draft=draft)
    out = publish_prepared(
        paths,
        upload_id=upload_id,
        title=title,
        description=description,
        price_eur=price_eur,
        category_leaf_id=leaf,
        lat=lat,
        lon=lon,
        condition=condition,
        shipping=shipping,
        weight_kg=weight_kg,
        wire_draft=wire,
    )
    out["reused_suggest"] = False
    return out


def _public_item_url(item_id: str) -> str:
    try:
        listing = get_item(item_id)
    except (
        WallaHTTPError,
        WallaNotFoundError,
        WallaParseError,
        WallaUnsupportedError,
        ValueError,
        KeyError,
        TypeError,
    ):
        return f"{WEB_BASE}/item/{item_id}"
    if listing.url:
        return listing.url
    if listing.web_slug:
        return item_url(listing.web_slug)
    return f"{WEB_BASE}/item/{item_id}"


def _upload_extra_pictures(item_id: str, photos: list[Path]) -> None:
    headers = {k: v for k, v in auth_headers().items() if k.lower() != "content-type"}
    headers["Accept"] = _UPLOAD_ACCEPT
    session: Any = requests.Session()
    for idx, path in enumerate(photos, start=1):
        data = path.read_bytes()
        ctype = IMAGE_TYPES.get(path.suffix.lower(), "image/jpeg")
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
