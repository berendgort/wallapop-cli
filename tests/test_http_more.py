"""More HTTP client and parse edge coverage."""

from __future__ import annotations

from typing import Any

import pytest

from walla.core.exceptions import WallaForbiddenError, WallaHTTPError
from walla.http import polite
from walla.http.client import HttpClient
from walla.http.polite import reset_polite
from walla.search.parse import parse_item, parse_listing_row, parse_search


def setup_function() -> None:
    reset_polite()


class _Resp:
    def __init__(self, status: int, payload: Any = None, text: str = "{}"):
        self.status_code = status
        self._payload = payload if payload is not None else {}
        self.headers: dict[str, str] = {}
        self.content = b"x" if payload is not None else b""
        self.text = text

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("bad json")
        return self._payload


def test_client_get_post_delete(monkeypatch: pytest.MonkeyPatch) -> None:
    client = HttpClient()
    monkeypatch.setattr(polite, "wait_turn", lambda **_: None)

    def ok(*a: Any, **k: Any) -> Any:
        return _Resp(200, {"hi": 1})

    monkeypatch.setattr(client._session, "request", ok)
    assert client.get("/x")["hi"] == 1
    assert client.post("/x", json_body={"a": 1})["hi"] == 1
    assert client.delete("/x")["hi"] == 1


def test_client_403_trips(monkeypatch: pytest.MonkeyPatch) -> None:
    client = HttpClient()
    monkeypatch.setattr(polite, "wait_turn", lambda **_: None)
    monkeypatch.setattr(client._session, "request", lambda *a, **k: _Resp(403, text="Forbidden"))
    with pytest.raises(WallaForbiddenError):
        client._send("GET", "https://api.wallapop.com/x", headers={}, params={}, json_body=None)


def test_client_500(monkeypatch: pytest.MonkeyPatch) -> None:
    client = HttpClient()
    monkeypatch.setattr(polite, "wait_turn", lambda **_: None)
    monkeypatch.setattr(client._session, "request", lambda *a, **k: _Resp(500, text="err"))
    with pytest.raises(WallaHTTPError):
        client._send("GET", "https://api.wallapop.com/x", headers={}, params={}, json_body=None)


def test_client_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    client = HttpClient()
    monkeypatch.setattr(polite, "wait_turn", lambda **_: None)
    calls = {"n": 0}

    def once(*a: Any, **k: Any) -> Any:
        calls["n"] += 1
        return _Resp(200, {"n": calls["n"]})

    monkeypatch.setattr(client._session, "request", once)
    a = client.get("/cached", params={"q": 1}, use_cache=True)
    b = client.get("/cached", params={"q": 1}, use_cache=True)
    assert a == b
    assert calls["n"] == 1


def test_parse_legacy_search_objects() -> None:
    raw = {
        "search_objects": [
            {
                "id": "1",
                "title": "t",
                "price": {"amount": 10, "currency": "EUR"},
                "web_slug": "t-1",
            }
        ]
    }
    # parse_search expects data wrapper optionally
    result = parse_search({"data": raw})
    assert result.count == 1


def test_parse_item_taxonomy() -> None:
    raw = {
        "id": "1",
        "title": {"original": "Hello"},
        "description": {"original": "d"},
        "slug": "hello-1",
        "price": {"amount": 5, "currency": "EUR"},
        "taxonomy": [{"id": "17000", "name": "Bikes"}],
        "images": [],
    }
    item = parse_item(raw)
    assert item.category_id == 17000
    assert item.title == "Hello"


def test_parse_listing_shipping_flags() -> None:
    row = parse_listing_row(
        {
            "id": "1",
            "title": "t",
            "price": {"amount": 1, "currency": "EUR"},
            "web_slug": "t",
            "reserved": {"flag": True},
            "shipping": {"item_is_shippable": True, "user_allows_shipping": True},
            "images": [{"urls": {"small": "http://x"}}],
        }
    )
    assert row.reserved is True
    assert row.shippable is True
    assert row.image_url == "http://x"
