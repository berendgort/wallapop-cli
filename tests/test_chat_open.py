"""Chat open + offer-disabled regressions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from walla.account.actions import make_offer
from walla.account.chat import open_conversation
from walla.http.headers import default_headers
from walla.hunter.profile_store import save_profile
from walla.models.listing import Listing, ListingLocation, Money
from walla.models.profile import Profile


def test_headers_include_app_version() -> None:
    h = default_headers(device_id="d")
    assert h["X-AppVersion"] == "825980"
    assert "es-ES" in h["Accept-Language"]


def test_open_conversation_posts_item_id() -> None:
    client = MagicMock()
    client.post.return_value = {
        "conversation_id": "conv1",
        "item_id": "item1",
        "other_user_id": "user2",
        "channel": "chat.user2.conv1.me",
    }
    out = open_conversation("item1", client=client)
    assert out["conversation_id"] == "conv1"
    assert out["channel"].startswith("chat.")
    body = client.post.call_args.kwargs["json_body"]
    assert body == {"item_id": "item1"}
    assert "chat?itemId=item1" in out["chat_url"]


def test_make_offer_409_points_to_say(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WALLA_CONFIG_DIR", str(tmp_path))
    save_profile(
        Profile(lat=41.39, lon=2.17, pickup_km=50, budget=850),
        path=tmp_path / "profile.json",
    )
    item = Listing(
        id="wzv48vgrmdzl",
        title="North Reach",
        price=Money(amount=800, currency="EUR"),
        web_slug="north-reach",
        url="https://es.wallapop.com/item/north-reach",
        shippable=True,
        user_allows_shipping=True,
        location=ListingLocation(latitude=39.5, longitude=2.7),
    )
    with patch("walla.account.actions.get_item", return_value=item):
        with patch("walla.account.actions._auth_client") as auth:
            client = MagicMock()
            client.post.side_effect = RuntimeError(
                'HTTP 409: [{"error_code":"offer creation not allowed"}]'
            )
            auth.return_value = client
            with pytest.raises(Exception, match="walla say") as exc:
                make_offer("wzv48vgrmdzl", 656, confirm=True)
            assert "disabled" in str(exc.value).lower() or "409" in str(exc.value)
