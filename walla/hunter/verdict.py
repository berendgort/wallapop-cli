"""GRAB / LOOK / PASS scoring (pure)."""

from __future__ import annotations

import math

from walla.models.listing import Listing
from walla.models.profile import Profile

__all__ = (
    "geo_scope",
    "haversine_km",
    "matches_must",
    "score_listing",
)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def matches_must(listing: Listing, profile: Profile) -> bool:
    """True when every must_match token appears in title or description."""
    tokens = [t.lower() for t in profile.must_match if t.strip()]
    if not tokens:
        return True
    blob = f"{listing.title} {listing.description or ''}".lower()
    return all(tok in blob for tok in tokens)


def geo_scope(*, local: bool) -> dict[str, object]:
    """Search contract for agents. lat/lon on the wire is a ranking bias."""
    if local:
        return {
            "scope": "local",
            "distance_filter": True,
            "note": "Human asked nearby or pickup. PASS outside profile.km.",
        }
    return {
        "scope": "spain",
        "distance_filter": False,
        "note": (
            "Spain-wide. Shipping counts anywhere. "
            "Use --local only if the human asked nearby, pickup, or no shipping."
        ),
    }


def score_listing(listing: Listing, profile: Profile, *, local: bool = False) -> str:
    """Return GRAB / LOOK / PASS. Distance fences only when local=True."""
    if listing.reserved:
        return "PASS"
    if not matches_must(listing, profile):
        return "PASS"
    budget = profile.spend_cap
    if budget is not None and listing.price.amount > budget:
        return "PASS"
    if local and _outside_km(listing, profile):
        return "PASS"
    if budget is not None and listing.price.amount <= budget * 0.9:
        return "GRAB"
    return "LOOK"


def _outside_km(listing: Listing, profile: Profile) -> bool:
    if profile.lat is None or profile.lon is None or not listing.location:
        return False
    la, lo = listing.location.latitude, listing.location.longitude
    if la is None or lo is None:
        return False
    return haversine_km(profile.lat, profile.lon, la, lo) > profile.km
