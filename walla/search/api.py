"""Public Wallapop search / item / categories."""

from __future__ import annotations

from typing import Any

from walla.http.client import HttpClient
from walla.models.listing import Listing, SearchResult
from walla.models.profile import Category
from walla.search.parse import parse_categories, parse_item, parse_search

__all__ = (
    "get_categories",
    "get_item",
    "search_listings",
)


def search_listings(
    keywords: str,
    *,
    latitude: float,
    longitude: float,
    max_results: int = 40,
    min_price: float | None = None,
    max_price: float | None = None,
    category_id: int | None = None,
    order_by: str = "most_relevance",
    next_page: str | None = None,
    client: HttpClient | None = None,
) -> SearchResult:
    http = client or HttpClient()
    collected: list[Listing] = []
    cursor = next_page
    last: SearchResult | None = None
    while len(collected) < max_results:
        params: dict[str, Any] = {
            "source": "search_box",
            "keywords": keywords,
            "latitude": latitude,
            "longitude": longitude,
            "order_by": order_by,
        }
        if min_price is not None:
            params["min_sale_price"] = min_price
        if max_price is not None:
            params["max_sale_price"] = max_price
        if category_id is not None:
            params["category_id"] = category_id
        if cursor:
            params["next_page"] = cursor
        raw = http.get("/api/v3/search", params=params, use_cache=True)
        page = parse_search(raw)
        last = page
        if not page.listings:
            break
        collected.extend(page.listings)
        if not page.next_page:
            break
        cursor = page.next_page
    listings = collected[:max_results]
    return SearchResult(
        listings=listings,
        next_page=last.next_page if last else None,
        count=len(listings),
    )


def get_item(item_id: str, *, client: HttpClient | None = None) -> Listing:
    http = client or HttpClient()
    raw = http.get(f"/api/v3/items/{item_id}", use_cache=True)
    return parse_item(raw)


def get_categories(*, client: HttpClient | None = None) -> list[Category]:
    http = client or HttpClient()
    raw = http.get("/api/v3/categories", use_cache=True)
    return parse_categories(raw)
