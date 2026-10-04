"""Session store and cookie parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from walla.account.cookies import parse_cookie_export
from walla.account.session_store import clear_session, load_session, save_session
from walla.core.exceptions import WallaAuthError
from walla.models.account import SessionData


def test_session_mode_0600(tmp_path: Path) -> None:
    path = tmp_path / "session.json"
    save_session(SessionData(access_token="tok", device_id="d"), path=path)
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    loaded = load_session(path)
    assert loaded is not None
    assert loaded.access_token == "tok"
    clear_session(path)
    assert load_session(path) is None


def test_parse_netscape_cookie(tmp_path: Path) -> None:
    f = tmp_path / "c.txt"
    f.write_text(
        "# Netscape\n"
        ".wallapop.com\tTRUE\t/\tTRUE\t0\t__Secure-next-auth.session-token\tabc.def.ghi\n"
        ".wallapop.com\tTRUE\t/\tFALSE\t0\tdevice_id\tdev-1\n",
        encoding="utf-8",
    )
    cookie, device = parse_cookie_export(f)
    assert cookie == "abc.def.ghi"
    assert device == "dev-1"


def test_parse_json_cookie(tmp_path: Path) -> None:
    f = tmp_path / "c.json"
    f.write_text(
        '[{"name":"__Secure-next-auth.session-token","value":"tok.a.b"},'
        '{"name":"device_id","value":"d2"}]',
        encoding="utf-8",
    )
    cookie, device = parse_cookie_export(f)
    assert cookie.startswith("tok")
    assert device == "d2"


def test_parse_cookie_missing(tmp_path: Path) -> None:
    f = tmp_path / "empty.txt"
    f.write_text("foo=bar\n", encoding="utf-8")
    with pytest.raises(WallaAuthError):
        parse_cookie_export(f)
