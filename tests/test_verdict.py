"""Hunter verdicts and watches."""

from __future__ import annotations

from walla.hunter.verdict import haversine_km, score_listing
from walla.hunter.watches import Watch, diff_new_ids, merge_seen
from walla.models.listing import Listing, ListingLocation, Money
from walla.models.profile import Profile


def _listing(**kwargs: object) -> Listing:
    base = dict(
        id="1",
        title="x",
        price=Money(amount=100, currency="EUR"),
        web_slug="x-1",
        url="https://es.wallapop.com/item/x-1",
        reserved=False,
        location=ListingLocation(latitude=41.39, longitude=2.17, city="BCN"),
    )
    base.update(kwargs)
    return Listing(**base)  # type: ignore[arg-type]


def test_haversine() -> None:
    d = haversine_km(41.39, 2.17, 41.40, 2.18)
    assert 0 < d < 5


def test_verdict_pass_reserved() -> None:
    p = Profile(lat=41.39, lon=2.17, budget=200)
    assert score_listing(_listing(reserved=True), p) == "PASS"


def test_verdict_pass_over_budget() -> None:
    p = Profile(lat=41.39, lon=2.17, budget=50)
    assert score_listing(_listing(price=Money(amount=100, currency="EUR")), p) == "PASS"


def test_verdict_grab() -> None:
    p = Profile(lat=41.39, lon=2.17, km=30, budget=200)
    assert score_listing(_listing(price=Money(amount=100, currency="EUR")), p) == "GRAB"


def test_far_shipping_is_grab_unless_local() -> None:
    p = Profile(lat=41.39, lon=2.17, km=30, budget=800)
    far = _listing(
        price=Money(amount=700, currency="EUR"),
        user_allows_shipping=True,
        shippable=True,
        location=ListingLocation(latitude=39.53, longitude=2.72, city="Mallorca"),
    )
    assert score_listing(far, p) == "GRAB"
    assert score_listing(far, p, local=True) == "PASS"


def test_far_pickup_stays_visible() -> None:
    p = Profile(lat=41.39, lon=2.17, km=5, budget=500)
    far = _listing(
        price=Money(amount=400, currency="EUR"),
        user_allows_shipping=False,
        location=ListingLocation(latitude=40.4, longitude=-3.7, city="Madrid"),
    )
    assert score_listing(far, p) == "GRAB"
    assert score_listing(far, p, local=True) == "PASS"


def test_watch_diff_and_merge() -> None:
    assert diff_new_ids(["a"], ["a", "b"]) == ["b"]
    w = Watch(id="1", keywords="bici", seen_ids=["a"])
    w2 = merge_seen(w, ["a", "b"])
    assert w2.seen_ids == ["a", "b"]
