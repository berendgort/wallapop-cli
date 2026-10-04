"""Favorites and offers."""

from __future__ import annotations

from typing import Any

from walla.account.login import ensure_access_token
from walla.account.offer_wire import build_offer_body
from walla.core.exceptions import WallaUnsupportedError
from walla.http.client import HttpClient
from walla.hunter.profile_store import load_profile
from walla.hunter.verdict import haversine_km
from walla.models.account import OfferQuote
from walla.models.listing import Listing
from walla.search.api import get_item

__all__ = (
    "add_favorite",
    "list_favorites",
    "make_offer",
    "quote_offer",
    "remove_favorite",
)

PROTECTION_PCT = 0.09
SHIPPING_EUR = 4.0


def _auth_client() -> HttpClient:
    sess = ensure_access_token()
    return HttpClient(access_token=sess.access_token, device_id=sess.device_id)


def list_favorites(*, client: HttpClient | None = None) -> list[dict[str, Any]]:
    http = client or _auth_client()
    for path in ("/api/v3/users/me/favorites", "/api/v3/favorites"):
        try:
            raw = http.get(path, auth=True)
            if isinstance(raw, dict):
                items = raw.get("data") or raw.get("items") or raw.get("favorites") or []
                if isinstance(items, list):
                    return [i for i in items if isinstance(i, dict)]
            if isinstance(raw, list):
                return [i for i in raw if isinstance(i, dict)]
        except Exception:  # noqa: BLE001
            continue
    raise WallaUnsupportedError("Favorites list wire not confirmed. Update docs/WIRE.md.")


def add_favorite(item_id: str, *, client: HttpClient | None = None) -> dict[str, Any]:
    http = client or _auth_client()
    try:
        raw = http.post(f"/api/v3/items/{item_id}/favorite", auth=True)
        return {"favorited": True, "item_id": item_id, "response": raw}
    except Exception as exc:
        raise WallaUnsupportedError(f"Favorite add failed: {exc}") from exc


def remove_favorite(item_id: str, *, client: HttpClient | None = None) -> dict[str, Any]:
    http = client or _auth_client()
    try:
        raw = http.delete(f"/api/v3/items/{item_id}/favorite", auth=True)
        return {"favorited": False, "item_id": item_id, "response": raw}
    except Exception as exc:
        raise WallaUnsupportedError(f"Favorite remove failed: {exc}") from exc


def quote_offer(item: Listing, offer_eur: float) -> OfferQuote:
    protection = round(offer_eur * PROTECTION_PCT, 2)
    shipping = SHIPPING_EUR if item.shippable else 0.0
    profile = load_profile()
    within = True
    if (
        not item.user_allows_shipping
        and profile.lat is not None
        and profile.lon is not None
        and item.location
        and item.location.latitude is not None
        and item.location.longitude is not None
    ):
        dist = haversine_km(
            profile.lat,
            profile.lon,
            item.location.latitude,
            item.location.longitude,
        )
        within = dist <= profile.pickup_km
    return OfferQuote(
        item_id=item.id,
        offer_eur=offer_eur,
        protection_eur=protection,
        shipping_eur=shipping,
        total_eur=round(offer_eur + protection + shipping, 2),
        within_pickup=within,
    )


def make_offer(
    item_id: str,
    offer_eur: float,
    *,
    confirm: bool = False,
    client: HttpClient | None = None,
) -> dict[str, Any]:
    if not confirm:
        raise ValueError("offer requires confirm=True / --yes")
    item = get_item(item_id, client=client)
    profile = load_profile()
    cap = profile.spend_cap
    if cap is not None and offer_eur > cap:
        raise ValueError(
            f"Offer {offer_eur} EUR exceeds budget {cap} EUR. Refuse."
        )
    quote = quote_offer(item, offer_eur)
    if not quote.within_pickup:
        raise ValueError(
            f"In-person listing outside pickup radius ({item.title}). Refuse offer."
        )
    http = client or _auth_client()
    body = build_offer_body(item_id, offer_eur)
    try:
        raw = http.post(
            "/api/v3/delivery/buyer/offers",
            json_body=body,
            auth=True,
        )
        return {
            "sent": True,
            "offer_id": body["offer_id"],
            "quote": quote.model_dump(mode="json"),
            "title": item.title,
            "response": raw,
        }
    except Exception as exc:
        msg = str(exc)
        if "409" in msg or "offer creation not allowed" in msg.lower():
            raise WallaUnsupportedError(
                "Seller disabled formal offers (409). "
                "Open chat and send the price in text: "
                f'walla say {item_id} "… te propongo {offer_eur} € …" --yes'
            ) from exc
        raise WallaUnsupportedError(
            f"Offer wire failed ({exc}). Capture POST buyer/offers and update WIRE.md."
        ) from exc
