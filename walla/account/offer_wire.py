"""Buyer-offer request shape (fail closed; fixture-backed)."""

from __future__ import annotations

import uuid
from typing import Any

__all__ = (
    "FORBIDDEN_OFFER_KEYS",
    "REQUIRED_OFFER_KEYS",
    "assert_offer_body",
    "build_offer_body",
)

REQUIRED_OFFER_KEYS = (
    "offer_id",
    "offer_price_amount",
    "offer_price_currency",
    "item_ids",
)

# Old guessed shape that Wallapop rejected with HTTP 400.
FORBIDDEN_OFFER_KEYS = ("item_id", "amount", "currency")


def build_offer_body(
    item_id: str, offer_eur: float, *, offer_id: str | None = None
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "offer_id": offer_id or str(uuid.uuid4()),
        "offer_price_amount": offer_eur,
        "offer_price_currency": "EUR",
        "item_ids": [item_id],
    }
    assert_offer_body(body)
    return body


def assert_offer_body(body: dict[str, Any]) -> None:
    bad = [k for k in FORBIDDEN_OFFER_KEYS if k in body]
    if bad:
        raise ValueError(f"offer body has forbidden keys (HTTP 400 shape): {bad}")
    missing = [k for k in REQUIRED_OFFER_KEYS if k not in body]
    if missing:
        raise ValueError(f"offer body missing keys: {missing}")
    if not isinstance(body["item_ids"], list) or not body["item_ids"]:
        raise ValueError("offer body item_ids must be a non-empty list")
    if body["offer_price_currency"] != "EUR":
        raise ValueError("offer body currency must be EUR")
