"""CLI JSON envelope and secret hygiene."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from walla.cli.main import app
from walla.core.envelope import error_payload, success_payload
from walla.core.exceptions import WallaAuthError, WallaRateLimitError
from walla.hunter.profile_store import save_profile
from walla.models.listing import Listing, ListingLocation, Money
from walla.models.profile import Profile
from walla.search import api as search_api

runner = CliRunner()


def test_success_envelope() -> None:
    p = success_payload({"x": 1})
    assert p["ok"] is True
    assert p["api_version"] == 1
    assert p["data"]["x"] == 1


def test_auth_error_has_human_fix() -> None:
    p = error_payload(WallaAuthError("nope"))
    assert p["ok"] is False
    assert p["error_type"] == "auth"
    assert "human_fix" in p


def test_rate_limit_fields() -> None:
    p = error_payload(WallaRateLimitError("slow", retry_after_s=2.0))
    assert p["error_type"] == "rate_limited"
    assert p["retryable"] is True
    assert p["retry_after_s"] == 2.0


def test_instruct_json() -> None:
    result = runner.invoke(app, ["instruct", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["data"]["name"] == "walla"


def test_doctor_never_echoes_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WALLAPOP_PW", "super-secret-password-xyz")
    monkeypatch.setenv("WALLAPOP_USER", "user@example.com")
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    assert "super-secret-password-xyz" not in result.stdout


def test_setup_and_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    result = runner.invoke(
        app,
        [
            "setup",
            "--lat",
            "41.39",
            "--lon",
            "2.17",
            "--km",
            "25",
            "--label",
            "BCN",
            "--json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["data"]["ready"] is True


def test_offer_needs_confirm_without_yes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    save_profile(
        Profile(lat=41.39, lon=2.17, km=30, pickup_km=30, budget=500),
        path=tmp_path / "profile.json",
    )

    def fake_item(item_id: str, **kwargs: object) -> Listing:
        return Listing(
            id=item_id,
            title="Test bike",
            price=Money(amount=200, currency="EUR"),
            web_slug="test-bike",
            url="https://es.wallapop.com/item/test-bike",
            shippable=True,
            user_allows_shipping=True,
        )

    monkeypatch.setattr(search_api, "get_item", fake_item)
    monkeypatch.setattr("walla.cli.cmd_account.get_item", fake_item)
    monkeypatch.setattr("walla.account.actions.get_item", fake_item)
    result = runner.invoke(app, ["offer", "abc", "--eur", "150", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["data"]["needs_confirm"] is True


def test_offer_refuses_outside_pickup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from walla.account.actions import make_offer

    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    save_profile(
        Profile(lat=41.39, lon=2.17, km=5, pickup_km=5, budget=500),
        path=tmp_path / "profile.json",
    )

    def fake_item(item_id: str, **kwargs: object) -> Listing:
        return Listing(
            id=item_id,
            title="Far away",
            price=Money(amount=100, currency="EUR"),
            web_slug="far",
            url="https://es.wallapop.com/item/far",
            shippable=False,
            user_allows_shipping=False,
            location=ListingLocation(latitude=40.4, longitude=-3.7, city="Madrid"),
        )

    monkeypatch.setattr("walla.account.actions.get_item", fake_item)
    with pytest.raises(ValueError, match="pickup"):
        make_offer("xyz", 80, confirm=True)


def test_say_requires_confirm() -> None:
    from walla.account.inbox import send_message

    with pytest.raises(ValueError, match="confirm"):
        send_message("c1", "hola", confirm=False)
