"""Pursue sends a wave. Desk answers from one inbox read. Human still closes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from walla.account.desk import run_desk, run_pursue
from walla.hunter.converge import next_move
from walla.hunter.pursuits import Pursuit, remember
from walla.hunter.stack import stack_summary
from walla.models.account import Message
from walla.models.listing import Listing, ListingLocation, Money
from walla.models.profile import Profile


def _msg(text: str, *, mine: bool, at: int = 1) -> Message:
    return Message(text=text, from_self=mine, created_at=at)


def _buy(**kwargs: Any) -> Pursuit:
    base: dict[str, Any] = {
        "item_id": "i1",
        "title": "Tabla kite",
        "url": "https://es.wallapop.com/item/tabla",
        "side": "buy",
        "ask_eur": 200,
        "offer_eur": 164,
        "walk_away_eur": 200,
        "status": "waiting",
    }
    base.update(kwargs)
    return Pursuit(**base)


def test_waiting_without_echo_does_not_send_again() -> None:
    move = next_move(_buy(), [])
    assert move.action == "wait"


def test_first_contact_sends_when_still_open() -> None:
    move = next_move(_buy(status="open"), [])
    assert move.action == "send"
    assert "164" in move.text
    assert "¿Sigue disponible?" in move.text


def test_seller_price_inside_ceiling_converges() -> None:
    move = next_move(
        _buy(),
        [_msg("Te propongo 164 €", mine=True, at=1), _msg("te lo dejo en 170 €", mine=False, at=2)],
    )
    assert move.action == "converged"
    assert move.agreed_eur == 170


def test_seller_above_ceiling_after_our_max_walks() -> None:
    move = next_move(
        _buy(offer_eur=200, walk_away_eur=200),
        [_msg("200 €", mine=True, at=1), _msg("lo mínimo 230 €", mine=False, at=2)],
    )
    assert move.action == "walk"


def test_counter_steps_up_but_not_over_ceiling() -> None:
    move = next_move(
        _buy(offer_eur=160, walk_away_eur=180),
        [_msg("160 €", mine=True, at=1), _msg("lo dejo en 190 €", mine=False, at=2)],
    )
    assert move.action == "send"
    assert move.offer_eur == 175
    assert "175" in move.text


def test_vale_converges_and_no_does_not() -> None:
    thread = [_msg("164 €", mine=True, at=1), _msg("vale", mine=False, at=2)]
    assert next_move(_buy(), thread).action == "converged"
    refused = [_msg("164 €", mine=True, at=1), _msg("no, no me vale", mine=False, at=2)]
    assert next_move(_buy(), refused).action == "send"
    assert next_move(_buy(nudges=1), refused).action == "wait"


def test_sell_holds_floor() -> None:
    sale = _buy(side="sell", ask_eur=50, offer_eur=50, walk_away_eur=45, status="waiting")
    low = next_move(
        sale,
        [_msg("Lo dejo en 50 €", mine=True, at=1), _msg("te doy 30 €", mine=False, at=2)],
    )
    assert low.action == "send"
    assert low.offer_eur is not None and low.offer_eur >= 45
    met = next_move(
        sale,
        [_msg("50 €", mine=True, at=1), _msg("va, 46 €", mine=False, at=2)],
    )
    assert met.action == "converged"
    assert met.agreed_eur == 46


def test_stack_picks_cheapest_buy() -> None:
    cheap = _buy(item_id="a", title="Barata", agreed_eur=90, status="converged")
    dear = _buy(item_id="b", title="Cara", agreed_eur=140, status="converged")
    summary = stack_summary([dear, cheap])
    assert isinstance(summary["best"], dict)
    assert summary["best"]["item_id"] == "a"  # type: ignore[index]
    assert "Barata" in str(summary["why"])
    assert summary["close_in_app"] is True


def test_pursue_sends_once_and_desk_does_not_repeat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    listing = Listing(
        id="item1",
        title="Tabla kite Cabrinha Moto 10m",
        price=Money(amount=100, currency="EUR"),
        web_slug="tabla",
        url="https://es.wallapop.com/item/tabla",
        shippable=True,
        user_allows_shipping=True,
        location=ListingLocation(latitude=41.39, longitude=2.17),
    )
    sent: list[str] = []

    def _search(*_a: Any, **_k: Any) -> Any:
        class Page:
            listings = [listing]

        return Page()

    def _send(
        target: str,
        text: str,
        *,
        confirm: bool = False,
        client: Any = None,
    ) -> dict[str, str]:
        assert confirm is True
        sent.append(text)
        return {"sent": "1"}

    monkeypatch.setattr("walla.account.desk.search_listings", _search)
    monkeypatch.setattr("walla.account.desk.send_message", _send)
    monkeypatch.setattr(
        "walla.account.desk.load_profile",
        lambda: Profile(lat=41.39, lon=2.17, budget=400, pickup_km=30),
    )
    monkeypatch.setattr(
        "walla.account.desk.list_conversations_raw",
        lambda **_k: {"conversations": []},
    )
    first = run_pursue("kite")
    assert len(first["sent"]) == 1
    assert "¿Sigue disponible?" in sent[0]
    again = run_pursue("kite")
    assert again["sent"] == []
    assert len(sent) == 1


def test_desk_replies_from_one_inbox_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    remember(
        _buy(offer_eur=160, walk_away_eur=180),
        path=tmp_path / "pursuits.json",
    )
    calls: list[str] = []

    def _inbox(**_k: Any) -> dict[str, Any]:
        return {
            "conversations": [
                {
                    "hash": "c1",
                    "item": {"hash": "i1", "title": "Tabla kite", "slug": "tabla"},
                    "messages": {
                        "messages": [
                            {"text": "190 €", "from_self": False, "timestamp": 2, "type": "text"},
                            {"text": "160 €", "from_self": True, "timestamp": 1, "type": "text"},
                        ]
                    },
                }
            ]
        }

    monkeypatch.setattr("walla.account.desk.list_conversations_raw", _inbox)
    monkeypatch.setattr(
        "walla.account.desk.send_message",
        lambda target, text, **_k: calls.append(text) or {"sent": True},
    )
    out = run_desk()
    assert calls and "175" in calls[0]
    assert out["replies"][0]["action"] == "send"
    assert out["stack"]["close_in_app"] is True
