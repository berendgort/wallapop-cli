"""Every CLI Wallapop call must match fixtures/wire_contracts.json."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from urllib.parse import urlparse

import pytest

from walla.account.actions import list_favorites, make_offer
from walla.account.chat import open_conversation, publish_text
from walla.account.inbox import list_conversations_raw
from walla.account.login import login_password, mint_access_token, refresh_session, whoami
from walla.account.offer_wire import assert_offer_body
from walla.account.sell import delete_listing, publish_listing
from walla.account.sell_edit import edit_listing
from walla.account.sell_wire import assert_item_body, build_item_body
from walla.core.exceptions import WallaAuthError, WallaHTTPError, WallaUnsupportedError
from walla.http.client import HttpClient
from walla.http.polite import reset_polite
from walla.models.account import SessionData
from walla.models.listing import Listing, ListingLocation, Money
from walla.models.profile import Profile
from walla.search.api import get_categories, get_item, search_listings

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures"
CATALOG = json.loads((FIX / "wire_contracts.json").read_text(encoding="utf-8"))
CONTRACTS = CATALOG["requests"]
_SEARCH = json.loads((FIX / "search_bicicleta.json").read_text(encoding="utf-8"))
_ITEM = json.loads((FIX / "item_detail.json").read_text(encoding="utf-8"))
_CATS = json.loads((FIX / "categories.json").read_text(encoding="utf-8"))


class Hit:
    def __init__(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any] | None = None,
        parts: list[tuple[str, Any]] | None = None,
    ) -> None:
        self.method = method.upper()
        self.url = url
        self.headers = headers
        self.body = body
        self.parts = parts or []


class Rec(HttpClient):
    """HttpClient that records the real request() headers and returns fixtures."""

    def __init__(self, hits: list[Hit]) -> None:
        super().__init__(access_token="tok", device_id="dev-contract")
        self.hits = hits

    def _send(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        params: dict[str, Any],
        json_body: dict[str, Any] | None,
    ) -> Any:
        del params
        self.hits.append(Hit(method, url, dict(headers), json_body))
        path = urlparse(url).path
        status, payload = _canned(method, path)
        resp = MagicMock()
        resp.status_code = status
        resp.headers = {}
        if payload is None:
            resp.content = b""
            resp.text = ""
        else:
            raw = json.dumps(payload).encode()
            resp.content = raw
            resp.text = raw.decode()
            resp.json.return_value = payload
        return resp


def _canned(method: str, path: str) -> tuple[int, Any]:
    if path == "/api/v3/users/me/favorites":
        return 404, {"error": "missing"}
    if path == "/api/v3/search":
        return 200, _SEARCH
    if path == "/api/v3/categories":
        return 200, _CATS
    if path.startswith("/api/v3/items/") and method.upper() == "GET":
        return 200, _ITEM
    if path == "/bff/messaging/inbox":
        return 200, {"conversations": [], "user_hash": "me"}
    if path == "/api/v3/conversations":
        return 200, {"conversation_id": "c1", "other_user_id": "u2", "channel": "ch"}
    if path == "/api/v3/instant-messaging/token":
        return 200, {"token": "pn-token"}
    if path in ("/api/v3/favorites",) or path.endswith("/favorite"):
        return 200, {"data": []}
    if method.upper() == "DELETE":
        return 204, None
    return 200, {}


def _matches(hit: Hit, contract: dict[str, Any]) -> bool:
    if hit.method != contract["method"]:
        return False
    template = contract["path"]
    if template.startswith("http"):
        return hit.url.startswith(template)
    pattern = "^" + re.sub(r"\{[^/}]+\}", "[^/]+", template) + "$"
    return re.fullmatch(pattern, urlparse(hit.url).path) is not None


def _assert_hit(hit: Hit, contract: dict[str, Any]) -> None:
    host = urlparse(hit.url).hostname or ""
    if host.endswith("wallapop.com"):
        for name in CATALOG["shared_headers"]:
            assert name in hit.headers, contract["id"]
        assert hit.headers["X-DeviceOS"] == "0"
        assert hit.headers["X-AppVersion"]
    if contract.get("auth"):
        assert str(hit.headers.get("Authorization", "")).startswith("Bearer ")
    else:
        assert "Authorization" not in hit.headers
    accept = contract.get("accept")
    if isinstance(accept, str):
        assert hit.headers.get("Accept") == accept
    for key in contract.get("body_keys") or []:
        assert hit.body is not None and key in hit.body
    for key in contract.get("forbidden_body_keys") or []:
        assert hit.body is None or key not in hit.body
    names = [name for name, _data in hit.parts]
    for name in contract.get("multipart") or []:
        assert name in names, contract["id"]


@pytest.fixture(autouse=True)
def _quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_polite()
    for target in (
        "walla.http.client.wait_turn",
        "walla.account.sell.wait_turn",
        "walla.account.login.wait_turn",
    ):
        monkeypatch.setattr(target, lambda *a, **k: None)


def test_catalog_ids_unique() -> None:
    ids = [row["id"] for row in CONTRACTS]
    assert len(ids) == len(set(ids))


def test_every_contract_is_sent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hits: list[Hit] = []
    rec = Rec(hits)
    parts: list[tuple[str, Any]] = []

    def _addpart(self: Any, name: str, data: Any = None, **_k: Any) -> None:
        del self
        parts.append((name, data))

    class _Sess:
        def request(
            self,
            method: str,
            url: str,
            headers: dict[str, str] | None = None,
            **_k: Any,
        ) -> Any:
            snapped = list(parts)
            parts.clear()
            hits.append(Hit(method, url, dict(headers or {}), None, snapped))
            resp = MagicMock()
            path = urlparse(url).path
            if path == "/api/v3/items":
                resp.status_code = 200
                resp.content = b'{"id":"item123"}'
                resp.text = '{"id":"item123"}'
                resp.json.return_value = {"id": "item123", "flags": {}}
            else:
                resp.status_code = 204
                resp.content = b""
                resp.text = ""
            return resp

    def _get(url: str, headers: dict[str, str] | None = None, **_k: Any) -> Any:
        hits.append(Hit("GET", url, dict(headers or {})))
        resp = MagicMock()
        resp.status_code = 200
        resp.headers = {}
        resp.cookies.jar = []
        if url.endswith("/api/auth/session"):
            payload = {"token": "minted"}
        elif url.endswith("/users/me"):
            payload = {"data": {"id": "u1", "micro_name": "B"}}
        elif "pndsn.com" in url:
            resp.content = b'[1,"Sent"]'
            resp.text = '[1,"Sent"]'
            return resp
        else:
            resp.status_code = 500
            resp.content = b""
            resp.text = url
            return resp
        raw = json.dumps(payload).encode()
        resp.content = raw
        resp.text = raw.decode()
        resp.json.return_value = payload
        return resp

    def _post(
        url: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        **_k: Any,
    ) -> Any:
        hits.append(Hit("POST", url, dict(headers or {}), json))
        resp = MagicMock()
        resp.headers = {}
        if url.endswith("/access/login"):
            resp.status_code = 400
            resp.content = b""
            resp.text = ""
            return resp
        resp.status_code = 200
        payload = {"data": {"token": {"access_token": "a", "refresh_token": "b"}}}
        resp.content = b"{}"
        resp.text = "{}"
        resp.json.return_value = payload
        return resp

    monkeypatch.setattr("walla.account.login.requests.get", _get)
    monkeypatch.setattr("walla.account.login.requests.post", _post)
    monkeypatch.setattr("walla.account.chat.requests.get", _get)
    monkeypatch.setattr("walla.account.login.save_session", lambda _s: None)
    monkeypatch.setattr("walla.account.sell.requests.Session", lambda: _Sess())
    monkeypatch.setattr("walla.account.sell.CurlMime.addpart", _addpart)
    monkeypatch.setattr("walla.account.sell.CurlMime.close", lambda _s: None)
    monkeypatch.setattr("walla.account.sell_edit.requests.request", _Sess().request)
    monkeypatch.setattr(
        "walla.account.sell_edit.fetch_owned_item",
        lambda _id: {
            "title": {"original": "Cofre test"},
            "description": {"original": "desc"},
            "price": {"cash": {"amount": 79.0}},
            "type_attributes": {"condition": {"value": "good"}},
            "taxonomy": [{"id": 10328}],
            "location": {"latitude": 41.39, "longitude": 2.17},
            "shipping": {"user_allows_shipping": False},
            "images": [{"id": 1}],
        },
    )
    sess = SessionData(
        access_token="tok",
        device_id="dev-contract",
        expires_at=9_999_999_999,
    )
    monkeypatch.setattr("walla.account.login.ensure_access_token", lambda: sess)
    monkeypatch.setattr("walla.account.sell_steps.ensure_access_token", lambda: sess)
    monkeypatch.setattr("walla.account.sell.auth_client", lambda: rec)
    monkeypatch.setattr("walla.account.sell_steps.auth_client", lambda: rec)
    monkeypatch.setattr("walla.account.chat.ensure_access_token", _must_not_mint)
    monkeypatch.setattr(
        "walla.account.actions.load_profile",
        lambda: Profile(lat=41.39, lon=2.17, pickup_km=80),
    )

    search_listings("bicicleta", latitude=41.39, longitude=2.17, max_results=1, client=rec)
    get_item("pzpkpw831lj3", client=rec)
    get_categories(client=rec)
    mint_access_token(SessionData(session_cookie="cookie", device_id="dev-contract"))
    with pytest.raises(WallaAuthError):
        login_password(username="a@b.c", password="not-a-real-secret")
    refresh_session(SessionData(refresh_token="r", device_id="dev-contract"))
    who = whoami()
    assert who["authenticated"] is True
    list_conversations_raw(client=rec)
    opened = open_conversation("pzpkpw831lj3", client=rec)
    assert opened["conversation_id"] == "c1"
    sent = publish_text(
        channel="ch",
        conversation_id="c1",
        from_user_hash="me",
        to_user_hash="u2",
        text="hola",
        client=rec,
    )
    assert sent["sent"] is True
    make_offer("pzpkpw831lj3", 40, confirm=True, client=rec)
    favs = list_favorites(client=rec)
    assert favs == []
    from walla.account.actions import add_favorite, remove_favorite

    add_favorite("pzpkpw831lj3", client=rec)
    remove_favorite("pzpkpw831lj3", client=rec)
    photo_a = tmp_path / "a.jpg"
    photo_b = tmp_path / "b.jpg"
    photo_a.write_bytes(b"\xff\xd8\xff\xd9")
    photo_b.write_bytes(b"\xff\xd8\xff\xd9")
    created = publish_listing(
        [photo_a, photo_b],
        title="Contrato",
        description="Una bici de prueba",
        price_eur=9,
        category_leaf_id="10105",
        root_category_id="12579",
        lat=41.39,
        lon=2.17,
    )
    assert created["id"] == "item123"
    edited = edit_listing("item123", price_eur=49.0)
    assert edited["edited"] is True
    assert edited["price_eur"] == 49.0
    delete_listing("item123", client=rec)

    item_parts = [
        data
        for hit in hits
        for name, data in hit.parts
        if name == "item" and isinstance(data, (bytes, bytearray))
    ]
    assert item_parts
    item_body = json.loads(item_parts[0])
    assert_item_body(item_body)
    assert isinstance(item_body["category_leaf_id"], str)

    missing = [
        row["id"]
        for row in CONTRACTS
        if not row.get("forbidden") and not any(_matches(hit, row) for hit in hits)
    ]
    assert missing == []
    for row in CONTRACTS:
        if row.get("forbidden"):
            assert not any(_matches(hit, row) for hit in hits), row["id"]
            continue
        hit = next(h for h in hits if _matches(h, row))
        _assert_hit(hit, row)
    offer = next(h for h in hits if h.url.endswith("/api/v3/delivery/buyer/offers"))
    assert offer.body is not None
    assert_offer_body(offer.body)


def _must_not_mint() -> SessionData:
    raise AssertionError("publish_text must not call ensure_access_token")


def test_forbidden_offer_shape_raises_before_http() -> None:
    hits: list[Hit] = []
    rec = Rec(hits)
    with pytest.raises(ValueError, match="forbidden"):
        assert_offer_body({"item_id": "x", "amount": 1, "currency": "EUR"})
    assert hits == []
    assert rec.hits == []


def test_offer_409_points_at_say(monkeypatch: pytest.MonkeyPatch) -> None:
    item = Listing(
        id="1",
        title="Mesa",
        price=Money(amount=20, currency="EUR"),
        web_slug="mesa",
        url="https://es.wallapop.com/item/mesa",
        shippable=True,
        user_allows_shipping=True,
        location=ListingLocation(latitude=41.39, longitude=2.17),
    )
    client = MagicMock()
    client.post.side_effect = WallaHTTPError(
        "HTTP 409: offer creation not allowed", status_code=409
    )
    monkeypatch.setattr("walla.account.actions.get_item", lambda *_a, **_k: item)
    monkeypatch.setattr(
        "walla.account.actions.load_profile",
        lambda: Profile(lat=41.39, lon=2.17, pickup_km=30),
    )
    with pytest.raises(WallaUnsupportedError, match="walla say"):
        make_offer("1", 10, confirm=True, client=client)


def test_category_leaf_id_is_a_string() -> None:
    body = build_item_body(
        upload_id="u",
        title="Tabla",
        description="Poco uso",
        price_eur=9,
        category_leaf_id="10105",
        lat=41.39,
        lon=2.17,
    )
    assert body["category_leaf_id"] == "10105"
    assert isinstance(body["category_leaf_id"], str)
