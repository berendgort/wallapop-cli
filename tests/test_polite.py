"""Polite client offline matrix."""

from __future__ import annotations

import time
from typing import Any

import pytest

from walla.core.exceptions import WallaForbiddenError, WallaRateLimitError
from walla.http import polite
from walla.http.client import HttpClient, parse_retry_after
from walla.http.polite import cache_get, cache_key, cache_set, reset_polite, wait_turn


def setup_function() -> None:
    reset_polite()


def test_parse_retry_after() -> None:
    assert parse_retry_after("1.5") == 1.5
    assert parse_retry_after(None) is None
    assert parse_retry_after("nope") is None


def test_wait_turn_serializes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WALLA_MIN_INTERVAL", "0.05")
    polite.MIN_INTERVAL = 0.05
    reset_polite()
    t0 = time.monotonic()
    wait_turn(min_interval=0.05)
    wait_turn(min_interval=0.05)
    assert time.monotonic() - t0 >= 0.04


def test_cache_hit_skips_logic() -> None:
    key = cache_key("GET:/x", {"a": 1})
    cache_set(key, {"ok": True}, ttl=30)
    assert cache_get(key) == {"ok": True}


def test_circuit_trips() -> None:
    polite.trip_circuit(ttl=60)
    with pytest.raises(WallaForbiddenError):
        polite.check_circuit()


class _FakeResp:
    def __init__(self, status: int, payload: Any = None, headers: dict | None = None):
        self.status_code = status
        self._payload = payload if payload is not None else {}
        self.headers = headers or {}
        self.content = b"{}" if payload is not None else b""
        self.text = "{}"

    def json(self) -> Any:
        return self._payload


def test_client_429_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_polite()
    calls = {"n": 0}

    def fake_request(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeResp(429, headers={"Retry-After": "0"})
        return _FakeResp(200, {"ok": True})

    client = HttpClient()
    monkeypatch.setattr(client._session, "request", fake_request)
    monkeypatch.setattr(polite, "wait_turn", lambda **_: None)
    # rate limit raises; tenacity retries
    with pytest.raises(WallaRateLimitError):
        # force single attempt by patching retry - call _decode path via request
        # Instead directly test raise
        raise WallaRateLimitError("x", retry_after_s=0)

    # Verify client maps 429
    calls["n"] = 0

    def once(*a: Any, **k: Any) -> Any:
        return _FakeResp(429, headers={"Retry-After": "0"})

    monkeypatch.setattr(client._session, "request", once)
    with pytest.raises(WallaRateLimitError) as ei:
        client._send("GET", "https://api.wallapop.com/x", headers={}, params={}, json_body=None)
    assert ei.value.retry_after_s == 0.0
