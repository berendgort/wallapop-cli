"""Account layer unit tests with mocks."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from walla.account.actions import quote_offer
from walla.account.inbox import list_conversations, list_messages
from walla.account.login import login_password
from walla.core.exceptions import WallaAuthError, WallaUnsupportedError
from walla.http.client import HttpClient
from walla.hunter.profile_store import save_profile
from walla.models.listing import Listing, ListingLocation, Money
from walla.models.profile import Profile


def test_quote_offer_totals(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    save_profile(Profile(lat=41.39, lon=2.17, pickup_km=30), path=tmp_path / "profile.json")
    item = Listing(
        id="1",
        title="x",
        price=Money(amount=100, currency="EUR"),
        web_slug="x",
        url="https://es.wallapop.com/item/x",
        shippable=True,
        user_allows_shipping=True,
    )
    q = quote_offer(item, 100)
    assert q.total_eur > 100
    assert q.within_pickup is True


def test_list_conversations_bff_mock() -> None:
    class C(HttpClient):
        def request(self, method: str, path: str, **kwargs: Any) -> Any:  # type: ignore[override]
            assert path == "/bff/messaging/inbox"
            return {
                "user_hash": "me",
                "conversations": [
                    {
                        "hash": "c1",
                        "item": {"hash": "i1", "title": "Bike"},
                        "with_user": {"hash": "u2", "name": "Ana"},
                        "unread_messages": 1,
                        "channel": "chat.u2.c1.me",
                        "messages": {
                            "messages": [{"id": "m1", "text": "hola", "from_self": False}]
                        },
                    }
                ],
            }

    with patch("walla.account.inbox._auth_client", return_value=C()):
        rows = list_conversations()
        msgs = list_messages("c1")
    assert rows[0].id == "c1"
    assert rows[0].item_title == "Bike"
    assert rows[0].other_user == "Ana"
    assert msgs[0].text == "hola"


def test_login_password_missing_args() -> None:
    with pytest.raises(WallaAuthError):
        login_password(username="", password="")


def test_login_password_empty_400() -> None:
    class Resp:
        status_code = 400
        content = b""

        def json(self) -> dict[str, Any]:
            return {}

    with patch("walla.account.login.requests.post", return_value=Resp()):
        with patch("walla.account.login.wait_turn"):
            with pytest.raises(WallaAuthError, match="Password login failed"):
                login_password(username="u@x.com", password="secret")


def test_favorites_unsupported() -> None:
    from walla.account.actions import list_favorites

    class C(HttpClient):
        def request(self, method: str, path: str, **kwargs: Any) -> Any:  # type: ignore[override]
            raise RuntimeError("nope")

    with patch("walla.account.actions._auth_client", return_value=C()):
        with pytest.raises(WallaUnsupportedError):
            list_favorites()


def test_make_offer_confirm_and_wire(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from walla.account.actions import make_offer

    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    save_profile(
        Profile(lat=41.39, lon=2.17, pickup_km=50),
        path=tmp_path / "profile.json",
    )
    item = Listing(
        id="1",
        title="Near",
        price=Money(amount=50, currency="EUR"),
        web_slug="near",
        url="https://es.wallapop.com/item/near",
        shippable=True,
        user_allows_shipping=True,
        location=ListingLocation(latitude=41.39, longitude=2.17),
    )
    with patch("walla.account.actions.get_item", return_value=item):
        with patch("walla.account.actions._auth_client") as auth:
            client = MagicMock()
            client.post.return_value = {"ok": True}
            auth.return_value = client
            out = make_offer("1", 40, confirm=True)
            assert out["sent"] is True
            assert out["quote"]["offer_eur"] == 40
            body = client.post.call_args.kwargs["json_body"]
            assert body["item_ids"] == ["1"]
            assert body["offer_price_amount"] == 40
            assert body["offer_price_currency"] == "EUR"
            assert body["offer_id"] == out["offer_id"]
