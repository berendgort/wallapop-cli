"""Parse Wallapop search / item JSON into Listing models."""

from __future__ import annotations

from typing import Any

from walla.core.exceptions import WallaParseError
from walla.models.listing import Listing, ListingLocation, Money, SearchResult
from walla.models.profile import Category

__all__ = (
    "item_url",
    "parse_categories",
    "parse_item",
    "parse_search",
)


def item_url(web_slug: str) -> str:
    return f"https://es.wallapop.com/item/{web_slug}"


def _flag(obj: Any) -> bool:
    if isinstance(obj, dict):
        return bool(obj.get("flag"))
    return bool(obj)


def _money(obj: Any) -> Money:
    if isinstance(obj, dict):
        amount = obj.get("amount")
        if isinstance(amount, dict):
            amount = amount.get("value") or amount.get("amount")
        currency = obj.get("currency") or "EUR"
        if amount is None:
            raise WallaParseError("missing price.amount")
        return Money(amount=float(amount), currency=str(currency))
    raise WallaParseError("invalid price")


def _location(obj: Any) -> ListingLocation | None:
    if not isinstance(obj, dict):
        return None
    return ListingLocation(
        latitude=obj.get("latitude"),
        longitude=obj.get("longitude"),
        city=obj.get("city"),
        postal_code=obj.get("postal_code"),
        region=obj.get("region"),
        country_code=obj.get("country_code"),
    )


def _image_url(images: Any) -> str | None:
    if not isinstance(images, list) or not images:
        return None
    first = images[0]
    if not isinstance(first, dict):
        return None
    urls = first.get("urls") or {}
    if isinstance(urls, dict):
        return urls.get("medium") or urls.get("small") or urls.get("big")
    return None


def parse_listing_row(raw: dict[str, Any]) -> Listing:
    web_slug = raw.get("web_slug") or raw.get("slug") or ""
    title = raw.get("title")
    if isinstance(title, dict):
        title = title.get("original") or title.get("text") or ""
    description = raw.get("description")
    if isinstance(description, dict):
        description = description.get("original") or description.get("text")
    shipping = raw.get("shipping") or {}
    price_raw = raw.get("price")
    if isinstance(price_raw, dict) and "amount" not in price_raw and "cash" in price_raw:
        price_raw = price_raw.get("cash")
    return Listing(
        id=str(raw["id"]),
        title=str(title or ""),
        description=str(description) if description else None,
        price=_money(price_raw),
        web_slug=str(web_slug),
        url=item_url(str(web_slug)) if web_slug else "",
        category_id=int(raw["category_id"]) if raw.get("category_id") is not None else None,
        reserved=_flag(raw.get("reserved")),
        shippable=bool(
            shipping.get("item_is_shippable")
            if isinstance(shipping, dict)
            else raw.get("supports_shipping")
        ),
        user_allows_shipping=bool(
            shipping.get("user_allows_shipping") if isinstance(shipping, dict) else False
        ),
        location=_location(raw.get("location")),
        image_url=_image_url(raw.get("images")),
        created_at=raw.get("created_at") or raw.get("modified_date"),
        modified_at=raw.get("modified_at") or raw.get("modified_date"),
        user_id=(raw.get("user_id") or (raw.get("user") or {}).get("id")),
    )


def parse_search(payload: dict[str, Any]) -> SearchResult:
    data = payload.get("data") or payload
    section = data.get("section") if isinstance(data, dict) else None
    items_raw: list[Any] = []
    if isinstance(section, dict):
        pl = section.get("payload") or {}
        items_raw = pl.get("items") or []
    elif isinstance(data, dict) and "search_objects" in data:
        items_raw = data["search_objects"]
    if not isinstance(items_raw, list):
        raise WallaParseError("search items missing")
    listings = [parse_listing_row(i) for i in items_raw if isinstance(i, dict)]
    meta = payload.get("meta") or {}
    next_page = meta.get("next_page") if isinstance(meta, dict) else None
    return SearchResult(listings=listings, next_page=next_page, count=len(listings))


def parse_item(payload: dict[str, Any]) -> Listing:
    raw = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if not isinstance(raw, dict) or "id" not in raw:
        raise WallaParseError("item payload missing id")
    # Detail endpoint uses title.original / slug
    if "web_slug" not in raw and "slug" in raw:
        raw = {**raw, "web_slug": raw["slug"]}
    if "category_id" not in raw and isinstance(raw.get("taxonomy"), list) and raw["taxonomy"]:
        tid = raw["taxonomy"][0].get("id")
        if tid is not None:
            raw = {**raw, "category_id": int(tid)}
    return parse_listing_row(raw)


def parse_categories(payload: dict[str, Any]) -> list[Category]:
    cats = payload.get("categories") or payload.get("data") or []
    if not isinstance(cats, list):
        raise WallaParseError("categories missing")
    return [_parse_category_node(c) for c in cats if isinstance(c, dict)]


def _parse_category_node(raw: dict[str, Any]) -> Category:
    kids_raw = raw.get("subcategories") or []
    kids: list[Category] = []
    if isinstance(kids_raw, list):
        kids = [_parse_category_node(c) for c in kids_raw if isinstance(c, dict)]
    return Category(
        id=int(raw["id"]),
        name=str(raw.get("name") or ""),
        icon=raw.get("icon") if isinstance(raw.get("icon"), str) else None,
        vertical_id=(
            str(raw["vertical_id"]) if raw.get("vertical_id") is not None else None
        ),
        subcategories=kids,
    )
