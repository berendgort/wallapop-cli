"""Seller create-item body (fixture-backed; fail closed)."""

from __future__ import annotations

from typing import Any

__all__ = (
    "CONDITIONS",
    "REQUIRED_ATTR_KEYS",
    "REQUIRED_ITEM_KEYS",
    "SELL_QUESTIONS",
    "assert_item_body",
    "build_item_body",
    "missing_sell_fields",
)

REQUIRED_ITEM_KEYS = (
    "attributes",
    "category_leaf_id",
    "apply_discount",
    "location",
    "delivery",
    "upload_id",
)

REQUIRED_ATTR_KEYS = ("title", "description", "price_amount")

CONDITIONS = (
    "as_good_as_new",
    "good",
    "fair",
    "has_given_it_all",
)

SELL_QUESTIONS = (
    {
        "id": "title",
        "ask": "Short title (max 50 chars). What are you selling?",
    },
    {
        "id": "description",
        "ask": "Full description: condition details, size, extras, why selling.",
    },
    {
        "id": "eur",
        "ask": "Asking price in EUR (number).",
    },
    {
        "id": "condition",
        "ask": "Condition: as_good_as_new | good | fair | has_given_it_all",
    },
    {
        "id": "category_leaf_id",
        "ask": "Leaf category id (string). Use walla categories --json to pick.",
    },
    {
        "id": "root_category_id",
        "ask": "Root category id (string), e.g. 12579 for Deporte y ocio.",
    },
    {
        "id": "shipping",
        "ask": "Allow Wallapop shipping? true/false. If true, weight_kg tier.",
    },
)


def build_item_body(
    *,
    upload_id: str,
    title: str,
    description: str,
    price_eur: float,
    category_leaf_id: str,
    lat: float,
    lon: float,
    condition: str | None = "good",
    shipping: bool = False,
    max_weight_kg: float | None = None,
) -> dict[str, Any]:
    attrs: dict[str, Any] = {
        "title": title.strip()[:50],
        "description": description.strip(),
        "price_amount": float(price_eur),
    }
    if condition:
        if condition not in CONDITIONS:
            raise ValueError(f"condition must be one of {CONDITIONS}")
        attrs["condition"] = condition
    body: dict[str, Any] = {
        "attributes": attrs,
        "category_leaf_id": str(category_leaf_id),
        "apply_discount": False,
        "location": {
            "latitude": float(lat),
            "longitude": float(lon),
            "approximated": True,
        },
        "delivery": {
            "allowed_by_user": bool(shipping),
            "max_weight_kg": float(max_weight_kg) if shipping and max_weight_kg else None,
            "cost_configuration_id": None,
        },
        "upload_id": upload_id,
    }
    assert_item_body(body)
    return body


def assert_item_body(body: dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_ITEM_KEYS if k not in body]
    if missing:
        raise ValueError(f"sell item body missing keys: {missing}")
    attrs = body["attributes"]
    if not isinstance(attrs, dict):
        raise ValueError("sell item attributes must be an object")
    for k in REQUIRED_ATTR_KEYS:
        if k not in attrs:
            raise ValueError(f"sell item attributes missing {k}")
    if not str(body["category_leaf_id"]):
        raise ValueError("category_leaf_id must be a non-empty string")
    loc = body["location"]
    if not isinstance(loc, dict) or "latitude" not in loc or "longitude" not in loc:
        raise ValueError("location needs latitude and longitude")


def missing_sell_fields(fields: dict[str, Any]) -> list[str]:
    """Return question ids still needed before publish."""
    need: list[str] = []
    if not str(fields.get("title") or "").strip():
        need.append("title")
    if not str(fields.get("description") or "").strip():
        need.append("description")
    if fields.get("eur") is None:
        need.append("eur")
    if not str(fields.get("category_leaf_id") or "").strip():
        need.append("category_leaf_id")
    if not str(fields.get("root_category_id") or "").strip():
        need.append("root_category_id")
    cond = fields.get("condition")
    if cond is not None and cond not in CONDITIONS:
        need.append("condition")
    if fields.get("shipping") is True and fields.get("weight_kg") is None:
        need.append("shipping")
    return need
