"""Edit an owned listing (PUT /api/v3/items/{id} + X-Signature)."""

from __future__ import annotations

import json
from typing import Any

from curl_cffi import requests

from walla.account.sell_edit_wire import build_edit_body
from walla.account.sell_steps import auth_client, auth_headers
from walla.core.exceptions import WallaHTTPError, WallaUnsupportedError
from walla.http.headers import API_BASE
from walla.http.polite import wait_turn
from walla.http.sign import signed_headers

__all__ = ("edit_listing", "fetch_owned_item")


def fetch_owned_item(item_id: str) -> dict[str, Any]:
    """GET /api/v3/items/{id} with auth (seller detail shape)."""
    raw = auth_client().get(f"/api/v3/items/{item_id}", auth=True)
    if not isinstance(raw, dict):
        raise WallaUnsupportedError("item detail returned non-object")
    return raw


def edit_listing(
    item_id: str,
    *,
    title: str | None = None,
    description: str | None = None,
    price_eur: float | None = None,
    shipping: bool | None = None,
    weight_kg: float | None = None,
) -> dict[str, Any]:
    """Patch title/description/price/shipping on an owned item. Needs --yes."""
    item = fetch_owned_item(item_id)
    cur_title = _orig(item.get("title"))
    cur_desc = _orig(item.get("description"))
    price_block = item.get("price") or {}
    cash = price_block.get("cash") if isinstance(price_block, dict) else None
    cur_price = float((cash or {}).get("amount") or 0)
    cond = ((item.get("type_attributes") or {}).get("condition") or {}).get("value")
    if not cond:
        raise WallaUnsupportedError("item missing type_attributes.condition")
    tax = item.get("taxonomy") or []
    if not tax:
        raise WallaUnsupportedError("item missing taxonomy leaf")
    leaf = str(tax[-1]["id"])
    loc = item.get("location") or {}
    ship = item.get("shipping") or {}
    allowed = bool(ship.get("user_allows_shipping"))
    pics = [
        {"id": img["id"], "order": i}
        for i, img in enumerate(item.get("images") or [])
        if isinstance(img, dict) and "id" in img
    ]
    body = build_edit_body(
        title=title if title is not None else cur_title,
        description=description if description is not None else cur_desc,
        price_eur=float(price_eur) if price_eur is not None else cur_price,
        category_leaf_id=leaf,
        condition=str(cond),
        lat=float(loc["latitude"]),
        lon=float(loc["longitude"]),
        pictures=pics,
        shipping=allowed if shipping is None else bool(shipping),
        max_weight_kg=weight_kg,
    )
    _put_edit(item_id, body)
    return {
        "id": item_id,
        "edited": True,
        "title": body["attributes"]["title"],
        "price_eur": body["attributes"]["price_amount"],
        "shipping": body["delivery"]["allowed_by_user"],
    }


def _orig(block: Any) -> str:
    if isinstance(block, dict):
        return str(block.get("original") or "")
    return str(block or "")


def _put_edit(item_id: str, body: dict[str, Any]) -> None:
    url = f"{API_BASE}/api/v3/items/{item_id}"
    headers = {k: v for k, v in auth_headers().items() if k.lower() != "content-type"}
    headers["Accept"] = "application/vnd.upload-v2+json"
    headers["Content-Type"] = "application/json"
    headers = signed_headers(method="PUT", url=url, base=headers)
    wait_turn()
    resp: Any = requests.request(
        "PUT",
        url,
        headers=headers,
        data=json.dumps(body).encode(),
        impersonate="chrome",
        timeout=30,
    )
    if resp.status_code not in (200, 201, 204):
        raise WallaHTTPError(
            f"edit item HTTP {resp.status_code}: {(resp.text or '')[:200]}",
            status_code=resp.status_code,
        )
