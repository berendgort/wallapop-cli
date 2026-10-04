"""Push remaining coverage edges."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from walla.account.actions import make_offer
from walla.account.cookies import parse_cookie_export
from walla.account.login import login_password, whoami
from walla.core.exceptions import WallaUnsupportedError
from walla.core.path import watches_path
from walla.http.polite import cache_key, cache_set, reset_polite
from walla.hunter.profile_store import save_profile
from walla.hunter.verdict import score_listing
from walla.models.listing import Listing, ListingLocation, Money
from walla.models.profile import Profile
from walla.search.api import search_listings
from walla.search.parse import parse_categories, parse_search


def test_search_with_filters() -> None:
    from walla.http.client import HttpClient

    class C(HttpClient):
        def request(self, method: str, path: str, **kwargs: Any) -> Any:  # type: ignore[override]
            assert kwargs.get("params", {}).get("min_sale_price") == 10
            assert kwargs.get("params", {}).get("max_sale_price") == 100
            assert kwargs.get("params", {}).get("category_id") == 17000
            return {
                "data": {"section": {"payload": {"items": []}}},
                "meta": {},
            }

    result = search_listings(
        "x",
        latitude=1.0,
        longitude=2.0,
        min_price=10,
        max_price=100,
        category_id=17000,
        client=C(),
    )
    assert result.count == 0


def test_parse_errors() -> None:
    from walla.core.exceptions import WallaParseError

    with pytest.raises(WallaParseError):
        parse_search({"data": {"section": {"payload": {"items": "bad"}}}})
    with pytest.raises(WallaParseError):
        parse_categories({"categories": "nope"})


def test_verdict_distance_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    p = Profile(lat=41.39, lon=2.17, km=5, budget=500)
    far = Listing(
        id="1",
        title="far",
        price=Money(amount=50, currency="EUR"),
        web_slug="f",
        url="https://es.wallapop.com/item/f",
        user_allows_shipping=False,
        location=ListingLocation(latitude=40.4, longitude=-3.7),
    )
    assert score_listing(far, p) == "GRAB"
    assert score_listing(far, p, local=True) == "PASS"


def test_cookie_bare_token(tmp_path: Path) -> None:
    f = tmp_path / "bare.txt"
    token = "a." + ("b" * 120) + ".c"
    f.write_text(token, encoding="utf-8")
    cookie, _ = parse_cookie_export(f)
    assert cookie.startswith("a.")


def test_login_success_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))

    class Resp:
        status_code = 200
        content = b"{}"

        def json(self) -> dict[str, Any]:
            return {"data": {"token": {"access_token": "A", "refresh_token": "R"}}}

    with patch("walla.account.login.requests.post", return_value=Resp()):
        with patch("walla.account.login.wait_turn"):
            sess = login_password(username="u@x.com", password="pw")
    assert sess.access_token == "A"


def test_whoami_404(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    from walla.account.session_store import save_session
    from walla.models.account import SessionData

    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    save_session(
        SessionData(access_token="t", expires_at=time.time() + 600, device_id="d"),
        path=tmp_path / "session.json",
    )

    class Resp:
        status_code = 404
        content = b""

    with patch("walla.account.login.requests.get", return_value=Resp()):
        with patch("walla.account.login.wait_turn"):
            info = whoami()
    assert info["authenticated"] is True


def test_make_offer_409(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    save_profile(Profile(lat=41.39, lon=2.17, pickup_km=50), path=tmp_path / "profile.json")
    item = Listing(
        id="1",
        title="x",
        price=Money(amount=10, currency="EUR"),
        web_slug="x",
        url="https://es.wallapop.com/item/x",
        user_allows_shipping=True,
        shippable=True,
        location=ListingLocation(latitude=41.39, longitude=2.17),
    )

    class Client:
        def post(self, *a: Any, **k: Any) -> Any:
            raise RuntimeError("HTTP 409 conflict")

    with patch("walla.account.actions.get_item", return_value=item):
        with patch("walla.account.actions._auth_client", return_value=Client()):
            with pytest.raises(WallaUnsupportedError, match="409"):
                make_offer("1", 8, confirm=True)


def test_watches_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    assert watches_path() == tmp_path / "watches.json"


def test_cache_eviction() -> None:
    reset_polite()
    from walla.http import polite

    polite.CACHE_MAX = 2
    cache_set(cache_key("a", {}), 1, ttl=60)
    cache_set(cache_key("b", {}), 2, ttl=60)
    cache_set(cache_key("c", {}), 3, ttl=60)
    polite.CACHE_MAX = 256
