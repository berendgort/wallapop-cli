"""Coverage helpers for core / dotenv / banner / path."""

from __future__ import annotations

from pathlib import Path

import pytest

from walla.cli.banner import print_banner
from walla.core.dotenv import credentials_configured, load_credentials, load_dotenv_files
from walla.core.errors import classify_error
from walla.core.exceptions import (
    WallaAmbiguousError,
    WallaNotFoundError,
    WallaParseError,
    WallaUnsupportedError,
)
from walla.core.path import config_dir, profile_path
from walla.http.polite import reset_polite
from walla.hunter.profile_store import parse_intake


def test_dotenv_and_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WALLAPOP_USER", raising=False)
    monkeypatch.delenv("WALLAPOP_PW", raising=False)
    monkeypatch.delenv("WALLAPOP_EMAIL", raising=False)
    monkeypatch.delenv("WALLAPOP_PASSWORD", raising=False)
    env = tmp_path / ".env"
    env.write_text("WALLAPOP_USER=a@b.c\nWALLAPOP_PW=hidden\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path / "cfg"))
    load_dotenv_files()
    user, pw = load_credentials()
    assert user == "a@b.c"
    assert pw == "hidden"
    assert credentials_configured() is True


def test_classify_types() -> None:
    assert classify_error(WallaNotFoundError("x")).error_type == "not_found"
    assert classify_error(WallaParseError("x")).error_type == "parse_error"
    assert classify_error(WallaUnsupportedError("x")).error_type == "unsupported"
    assert classify_error(WallaAmbiguousError("x", candidates=[])).error_type == "ambiguous"
    assert classify_error(ValueError("x")).error_type == "validation_error"
    assert classify_error(TimeoutError()).error_type == "timeout"


def test_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    assert config_dir() == tmp_path
    assert profile_path() == tmp_path / "profile.json"


def test_parse_intake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    p = parse_intake("lat=41.39 lon=2.17 km=20 pickup_km=10 label=Home budget=100")
    assert p.lat == 41.39
    assert p.budget == 100
    assert p.ready


def test_banner_no_crash(capsys: pytest.CaptureFixture[str]) -> None:
    reset_polite()
    print_banner()
