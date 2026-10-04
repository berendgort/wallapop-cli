"""Login / mint / inbox / watches coverage."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from walla.account.inbox import list_messages, send_message
from walla.account.login import (
    ensure_access_token,
    login_cookies,
    mint_access_token,
    refresh_session,
    whoami,
)
from walla.account.session_store import save_session
from walla.core.exceptions import WallaAuthError, WallaUnsupportedError
from walla.hunter.watches import Watch, WatchStore, load_watches, save_watches
from walla.models.account import SessionData


def test_mint_and_login_cookies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    cookie_file = tmp_path / "c.txt"
    cookie_file.write_text(
        "__Secure-next-auth.session-token=aaa.bbb.ccc\ndevice_id=dev\n",
        encoding="utf-8",
    )

    class Resp:
        status_code = 200
        content = b'{"token":"access.jwt.here"}'
        cookies = MagicMock(jar=[])

        def json(self) -> dict[str, str]:
            return {"token": "access.jwt.here"}

    with patch("walla.account.login.requests.get", return_value=Resp()):
        with patch("walla.account.login.wait_turn"):
            sess = login_cookies(cookie_file)
    assert sess.access_token == "access.jwt.here"
    assert sess.session_cookie


def test_mint_invalid_session() -> None:
    class Resp:
        status_code = 200
        content = b"{}"
        cookies = MagicMock(jar=[])

        def json(self) -> dict[str, Any]:
            return {}

    sess = SessionData(session_cookie="bad")
    with patch("walla.account.login.requests.get", return_value=Resp()):
        with patch("walla.account.login.wait_turn"):
            with pytest.raises(WallaAuthError):
                mint_access_token(sess)


def test_refresh_via_cookie(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    sess = SessionData(session_cookie="tok.a.b", device_id="d")
    save_session(sess, path=tmp_path / "session.json")

    class Resp:
        status_code = 200
        content = b'{"token":"new"}'
        cookies = MagicMock(jar=[])

        def json(self) -> dict[str, str]:
            return {"token": "new"}

    with patch("walla.account.login.requests.get", return_value=Resp()):
        with patch("walla.account.login.wait_turn"):
            out = refresh_session(sess)
    assert out.access_token == "new"


def test_refresh_via_refresh_token(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    sess = SessionData(refresh_token="r1", device_id="d")

    class Resp:
        status_code = 200
        content = b"{}"

        def json(self) -> dict[str, Any]:
            return {"data": {"token": {"access_token": "a2", "refresh_token": "r2"}}}

    with patch("walla.account.login.requests.post", return_value=Resp()):
        with patch("walla.account.login.wait_turn"):
            out = refresh_session(sess)
    assert out.access_token == "a2"
    assert out.refresh_token == "r2"


def test_ensure_access_token_cached(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    sess = SessionData(access_token="live", expires_at=time.time() + 600)
    save_session(sess, path=tmp_path / "session.json")
    out = ensure_access_token()
    assert out.access_token == "live"


def test_whoami_mock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import time

    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    sess = SessionData(
        access_token="t",
        device_id="d",
        expires_at=time.time() + 600,
    )
    save_session(sess, path=tmp_path / "session.json")

    class Resp:
        status_code = 200
        content = b"{}"

        def json(self) -> dict[str, Any]:
            return {"id": "u1", "micro_name": "Berend"}

    with patch("walla.account.login.requests.get", return_value=Resp()):
        with patch("walla.account.login.wait_turn"):
            info = whoami()
    assert info["micro_name"] == "Berend"
    assert info["authenticated"] is True


def test_list_messages_and_send() -> None:
    from walla.http.client import HttpClient

    class C(HttpClient):
        def request(self, method: str, path: str, **kwargs: Any) -> Any:  # type: ignore[override]
            if method == "GET":
                return {"messages": [{"id": "1", "text": "hi"}]}
            return {"ok": True}

    with patch("walla.account.inbox._auth_client", return_value=C()):
        msgs = list_messages("c1")
        assert msgs[0].text == "hi"
        out = send_message("c1", "hola", confirm=True)
        assert out["sent"] is True


def test_list_messages_unsupported() -> None:
    from walla.http.client import HttpClient

    class C(HttpClient):
        def request(self, method: str, path: str, **kwargs: Any) -> Any:  # type: ignore[override]
            raise RuntimeError("fail")

    with patch("walla.account.inbox._auth_client", return_value=C()):
        with pytest.raises(WallaUnsupportedError):
            list_messages("c1")


def test_watches_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    store = WatchStore(watches=[Watch(id="w1", keywords="bici")])
    save_watches(store, path=tmp_path / "watches.json")
    loaded = load_watches(path=tmp_path / "watches.json")
    assert loaded.watches[0].keywords == "bici"


def test_favorites_add_rm() -> None:
    from walla.account.actions import add_favorite, list_favorites, remove_favorite
    from walla.http.client import HttpClient

    class C(HttpClient):
        def request(self, method: str, path: str, **kwargs: Any) -> Any:  # type: ignore[override]
            if "favorites" in path and method == "GET":
                return {"items": [{"id": "1"}]}
            return {}

    with patch("walla.account.actions._auth_client", return_value=C()):
        assert list_favorites()[0]["id"] == "1"
        assert add_favorite("1")["favorited"] is True
        assert remove_favorite("1")["favorited"] is False
