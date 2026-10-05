"""Edit-item body (fixture-backed PUT /api/v3/items/{id})."""

from __future__ import annotations

from typing import Any

from walla.account.sell_wire import CONDITIONS

__all__ = (
    "EDIT_ATTR_KEYS",
    "EDIT_ITEM_KEYS",
    "assert_edit_body",
    "build_edit_body",
)

EDIT_ITEM_KEYS = (
    "attributes",
    "category_leaf_id",
    "apply_discount",
    "delivery",
    "location",
    "pictures",
)

EDIT_ATTR_KEYS = ("title", "description", "price_amount", "condition")


def build_edit_body(
    *,
    title: str,
    description: str,
    price_eur: float,
    category_leaf_id: str,
    condition: str,
    lat: float,
    lon: float,
    pictures: list[dict[str, Any]],
    shipping: bool = False,
    max_weight_kg: float | None = None,
    approximated: bool = False,
) -> dict[str, Any]:
    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {CONDITIONS}")
    if not pictures:
        raise ValueError("edit body needs at least one picture id")
    body: dict[str, Any] = {
        "attributes": {
            "title": title.strip()[:50],
            "description": description.strip(),
            "price_amount": float(price_eur),
            "condition": condition,
        },
        "category_leaf_id": str(category_leaf_id),
        "apply_discount": False,
        "delivery": {
            "allowed_by_user": bool(shipping),
            "max_weight_kg": (
                float(max_weight_kg) if shipping and max_weight_kg else None
            ),
            "cost_configuration_id": None,
        },
        "location": {
            "latitude": float(lat),
            "longitude": float(lon),
            "approximated": bool(approximated),
        },
        "pictures": pictures,
    }
    assert_edit_body(body)
    return body


def assert_edit_body(body: dict[str, Any]) -> None:
    missing = [k for k in EDIT_ITEM_KEYS if k not in body]
    if missing:
        raise ValueError(f"edit item body missing keys: {missing}")
    attrs = body["attributes"]
    if not isinstance(attrs, dict):
        raise ValueError("edit item attributes must be an object")
    for k in EDIT_ATTR_KEYS:
        if k not in attrs:
            raise ValueError(f"edit item attributes missing {k}")
    pics = body["pictures"]
    if not isinstance(pics, list) or not pics:
        raise ValueError("edit pictures must be a non-empty list")
