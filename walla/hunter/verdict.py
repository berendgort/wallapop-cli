"""GRAB / LOOK / PASS scoring (pure)."""

from __future__ import annotations

import math

from walla.models.listing import Listing
from walla.models.profile import Profile

__all__ = (
    "haversine_km",
    "score_listing",
)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def score_listing(listing: Listing, profile: Profile) -> str:
    """Return GRAB / LOOK / PASS."""
    if listing.reserved:
        return "PASS"
    budget = profile.budget or profile.max_price
    if budget is not None and listing.price.amount > budget:
        return "PASS"
    if profile.lat is not None and profile.lon is not None and listing.location:
        la, lo = listing.location.latitude, listing.location.longitude
        if la is not None and lo is not None:
            dist = haversine_km(profile.lat, profile.lon, la, lo)
            if dist > profile.km and not listing.user_allows_shipping:
                return "PASS"
            if budget is not None and listing.price.amount <= budget * 0.85 and dist <= profile.km:
                return "GRAB"
    if budget is not None and listing.price.amount <= budget * 0.9:
        return "GRAB"
    return "LOOK"
