"""Regression locks for past agent/wire failures."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from walla.account.actions import make_offer
from walla.account.offer_wire import (
    FORBIDDEN_OFFER_KEYS,
    REQUIRED_OFFER_KEYS,
    assert_offer_body,
    build_offer_body,
)
from walla.core.instruct import instruct_recipe
from walla.hunter.negotiate import draft_negotiation
from walla.hunter.profile_store import save_profile
from walla.hunter.shortlist import PRESENT_RULE, rank_shortlist
from walla.hunter.verdict import score_listing
from walla.models.listing import Listing, ListingLocation, Money
from walla.models.profile import Profile

FIX = Path(__file__).resolve().parents[1] / "fixtures"


def _listing(**kwargs: object) -> Listing:
    base: dict[str, object] = dict(
        id="wzv48vgrmdzl",
        title="North Reach 13m 2023",
        price=Money(amount=800, currency="EUR"),
        web_slug="north-reach-13m-2023",
        url="https://es.wallapop.com/item/north-reach-13m-2023",
        shippable=True,
        user_allows_shipping=True,
        location=ListingLocation(latitude=39.53, longitude=2.72, city="Mallorca"),
    )
    base.update(kwargs)
    return Listing(**base)  # type: ignore[arg-type]


def test_offer_fixture_matches_builder() -> None:
    meta = json.loads((FIX / "offer_buyer_request.json").read_text(encoding="utf-8"))
    assert tuple(meta["required_keys"]) == REQUIRED_OFFER_KEYS
    assert tuple(meta["forbidden_keys"]) == FORBIDDEN_OFFER_KEYS
    assert_offer_body(meta["example"])
    body = build_offer_body("wzv48vgrmdzl", 650, offer_id=meta["example"]["offer_id"])
    assert set(body) == set(REQUIRED_OFFER_KEYS)
    for k in FORBIDDEN_OFFER_KEYS:
        assert k not in body


def test_old_offer_shape_is_rejected() -> None:
    with pytest.raises(ValueError, match="forbidden"):
        assert_offer_body({"item_id": "x", "amount": 650, "currency": "EUR"})


def test_make_offer_posts_fixture_shape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    save_profile(
        Profile(lat=41.39, lon=2.17, pickup_km=50, budget=850),
        path=tmp_path / "profile.json",
    )
    with patch("walla.account.actions.get_item", return_value=_listing()):
        with patch("walla.account.actions._auth_client") as auth:
            client = MagicMock()
            client.post.return_value = {"ok": True}
            auth.return_value = client
            out = make_offer("wzv48vgrmdzl", 650, confirm=True)
            body = client.post.call_args.kwargs["json_body"]
            assert_offer_body(body)
            assert body["offer_price_amount"] == 650
            assert out["offer_id"] == body["offer_id"]


def test_fair_open_not_soft_90pct() -> None:
    profile = Profile(lat=41.39, lon=2.17, km=30, pickup_km=30, budget=850)
    brief = draft_negotiation(_listing(), profile)
    assert brief.offer_eur == 656
    assert brief.offer_eur < 800 * 0.90


def test_shipping_draft_never_says_paso_hoy() -> None:
    profile = Profile(lat=41.39, lon=2.17, km=30, pickup_km=30, budget=850)
    brief = draft_negotiation(_listing(), profile)
    blob = f"{brief.opening}\n{brief.offer_line}".lower()
    assert "envío" in blob
    assert "pasar hoy" not in blob
    assert "recojo" not in blob


def test_spain_default_keeps_far_shipping() -> None:
    profile = Profile(lat=41.39, lon=2.17, km=30, budget=850)
    far = _listing(price=Money(amount=700, currency="EUR"))
    assert score_listing(far, profile) == "GRAB"
    assert score_listing(far, profile, local=True) == "PASS"


def test_shortlist_ranked_with_wallapop_links() -> None:
    rows = [
        {
            "id": "a",
            "title": "A",
            "verdict": "LOOK",
            "price": {"amount": 700},
            "url": "https://es.wallapop.com/item/a",
        },
        {
            "id": "b",
            "title": "B",
            "verdict": "GRAB",
            "price": {"amount": 650},
            "url": "https://es.wallapop.com/item/b",
        },
    ]
    ranked = rank_shortlist(rows)
    assert [r["id"] for r in ranked] == ["b", "a"]
    assert all(r["url"].startswith("https://es.wallapop.com/item/") for r in ranked)
    assert "markdown" in PRESENT_RULE.lower()


def test_instruct_locks_present_and_spain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    data = instruct_recipe()
    assert data["present"]["channel"] == "wallapop.es"
    assert "es.wallapop.com/item" in data["present"]["format"]
    assert any("Spain" in r for r in data["rules"])
    assert any("--local" in r for r in data["rules"])
