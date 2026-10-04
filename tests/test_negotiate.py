"""Win-win negotiate drafts + HITL mandate."""

from __future__ import annotations

from pathlib import Path

import pytest

from walla.core.instruct import instruct_recipe
from walla.hunter.negotiate import BANNED_PHRASES, draft_negotiation
from walla.hunter.verdict import score_listing
from walla.models.listing import Listing, ListingLocation, Money
from walla.models.profile import Profile


def _listing(
    *,
    price: float = 100.0,
    lat: float = 41.39,
    lon: float = 2.17,
    ship: bool = False,
    title: str = "Tabla kite Cabrinha Moto 10m",
    description: str | None = None,
) -> Listing:
    return Listing(
        id="item1",
        title=title,
        description=description,
        price=Money(amount=price, currency="EUR"),
        web_slug="tabla-kite",
        url="https://es.wallapop.com/item/tabla-kite",
        shippable=ship,
        user_allows_shipping=ship,
        location=ListingLocation(latitude=lat, longitude=lon, city="Barcelona"),
    )


def test_draft_opening_is_specific_and_polite() -> None:
    profile = Profile(lat=41.39, lon=2.17, km=30, pickup_km=30, budget=400)
    brief = draft_negotiation(_listing(), profile, seller_name="Ana")
    assert "Ana" in brief.opening
    assert "¿Sigue disponible?" in brief.opening
    assert brief.needs_confirm is True
    assert brief.hitl == "approve_text_and_eur"
    blob = f"{brief.opening}\n{brief.offer_line}".lower()
    for phrase in BANNED_PHRASES:
        assert phrase not in blob
    assert not any(c.startswith("FAIL_") for c in brief.tone_checks)


def test_offer_band_never_lowballs() -> None:
    profile = Profile(lat=41.39, lon=2.17, km=30, pickup_km=30, budget=400)
    brief = draft_negotiation(_listing(price=200), profile)
    assert brief.offer_eur >= 200 * 0.80
    assert brief.offer_eur <= brief.walk_away_eur


def test_firm_offer_at_floor_within_budget() -> None:
    profile = Profile(
        lat=41.39, lon=2.17, km=30, pickup_km=30, budget=400, aggressiveness="firm"
    )
    brief = draft_negotiation(_listing(price=200), profile)
    assert brief.offer_eur >= 160
    assert brief.offer_eur <= 400
    assert brief.offer_eur == 160


def test_missing_budget_blocks_negotiate() -> None:
    profile = Profile(lat=41.39, lon=2.17, km=30, pickup_km=30)
    with pytest.raises(ValueError, match="set_budget"):
        draft_negotiation(_listing(), profile)


def test_must_match_pass() -> None:
    profile = Profile(
        lat=41.39,
        lon=2.17,
        km=30,
        pickup_km=30,
        budget=400,
        must_match=["cabrinha", "10m"],
    )
    assert score_listing(_listing(title="Tabla Dualox 9m"), profile) == "PASS"
    assert score_listing(_listing(), profile) == "GRAB"


def test_refuse_outside_pickup() -> None:
    profile = Profile(lat=41.39, lon=2.17, km=5, pickup_km=5, budget=500)
    far = _listing(price=50, lat=40.4, lon=-3.7, ship=False)
    with pytest.raises(ValueError, match="pickup"):
        draft_negotiation(far, profile)


def test_shipping_draft_asks_envio_not_pickup() -> None:
    profile = Profile(lat=41.39, lon=2.17, km=30, pickup_km=30, budget=800)
    brief = draft_negotiation(
        _listing(price=800, lat=39.53, lon=2.72, ship=True, title="North Reach 13m 2023"),
        profile,
    )
    blob = f"{brief.opening}\n{brief.offer_line}".lower()
    assert "envío" in blob
    assert "pasar hoy" not in blob
    assert "recojo" not in blob


def test_instruct_spain_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    data = instruct_recipe()
    assert data["hitl"]["never_pay"] is True
    assert data["hitl"]["yes_means"]
    assert any(s["step"] == "pay_or_buy" for s in data["hitl"]["ladder"])
    blob = " ".join(data["rules"]) + data["hitl"]["ladder"][0]["agent"]
    assert "Spain" in blob
    assert "--local" in blob
    assert "present" in data
    assert "wallapop.es" in data["present"]["channel"]
    assert "es.wallapop.com/item" in data["present"]["format"]
    assert "link" in data["hitl"]["ladder"][1]["agent"].lower()
