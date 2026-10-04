"""Pydantic listing models (no I/O)."""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = (
    "Listing",
    "ListingLocation",
    "Money",
    "SearchResult",
)


class Money(BaseModel):
    amount: float
    currency: str = "EUR"


class ListingLocation(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    city: str | None = None
    postal_code: str | None = None
    region: str | None = None
    country_code: str | None = None


class Listing(BaseModel):
    id: str
    title: str
    description: str | None = None
    price: Money
    web_slug: str
    url: str
    category_id: int | None = None
    reserved: bool = False
    shippable: bool = False
    user_allows_shipping: bool = False
    location: ListingLocation | None = None
    image_url: str | None = None
    created_at: int | None = None
    modified_at: int | None = None
    user_id: str | None = None
    verdict: str | None = None


class SearchResult(BaseModel):
    listings: list[Listing] = Field(default_factory=list)
    next_page: str | None = None
    count: int = 0
