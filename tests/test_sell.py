"""Sell wire fixture + draft questions."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from walla.account.sell_wire import (
    CONDITIONS,
    assert_item_body,
    build_item_body,
    missing_sell_fields,
)
from walla.core.exceptions import WallaHTTPError

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "sell_item_request.json"


def test_sell_fixture_matches_builder() -> None:
    meta = json.loads(FIXTURE.read_text(encoding="utf-8"))
    example = meta["example"]
    assert_item_body(example)
    body = build_item_body(
        upload_id=example["upload_id"],
        title=example["attributes"]["title"],
        description=example["attributes"]["description"],
        price_eur=float(example["attributes"]["price_amount"]),
        category_leaf_id=str(example["category_leaf_id"]),
        lat=float(example["location"]["latitude"]),
        lon=float(example["location"]["longitude"]),
        condition=example["attributes"]["condition"],
        shipping=False,
    )
    for key in meta["required_keys"]:
        assert key in body
    assert body["category_leaf_id"] == "10105"
    assert isinstance(body["category_leaf_id"], str)


def test_build_item_rejects_bad_condition() -> None:
    with pytest.raises(ValueError, match="condition"):
        build_item_body(
            upload_id="u",
            title="t",
            description="d",
            price_eur=1,
            category_leaf_id="1",
            lat=1.0,
            lon=2.0,
            condition="mint",
        )


def test_missing_sell_fields() -> None:
    assert "title" in missing_sell_fields({})
    assert missing_sell_fields(
        {
            "title": "x",
            "description": "y",
            "eur": 10,
            "category_leaf_id": "10105",
            "root_category_id": "12579",
            "condition": "good",
        }
    ) == []
    assert CONDITIONS[0] == "as_good_as_new"


def test_sell_cmd_draft_without_yes(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from walla.cli.main import app

    photo = tmp_path / "a.jpg"
    photo.write_bytes(b"\xff\xd8\xff\xd9")
    runner = CliRunner()
    with patch("walla.cli.cmd_sell.load_profile") as lp:
        profile = MagicMock()
        profile.lat = 41.39
        profile.lon = 2.17
        profile.label = "BCN"
        lp.return_value = profile
        result = runner.invoke(app, ["sell", str(photo), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["data"]["status"] == "draft"
    assert "title" in payload["data"]["missing"]


def test_sell_cmd_refuses_yes_when_incomplete(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from walla.cli.main import app

    photo = tmp_path / "a.jpg"
    photo.write_bytes(b"\xff\xd8\xff\xd9")
    runner = CliRunner()
    with patch("walla.cli.cmd_sell.load_profile") as lp:
        profile = MagicMock()
        profile.lat = 41.39
        profile.lon = 2.17
        profile.label = "BCN"
        lp.return_value = profile
        result = runner.invoke(app, ["sell", str(photo), "--yes", "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False


def test_publish_listing_mocked(tmp_path: Path) -> None:
    from walla.account.sell import publish_listing

    photo = tmp_path / "a.jpg"
    photo.write_bytes(b"\xff\xd8\xff\xd9")
    fake_http = MagicMock()
    fake_http.post.side_effect = [
        {"step": {"id": "title"}, "draft": {}},
        {"step": {"id": "photo"}, "draft": {"title": "Test item"}},
        {
            "step": {"id": "category"},
            "draft": {"title": "Test item", "category_leaf_id": "10105"},
        },
        {"step": {"id": "loading"}, "draft": {"title": "Test item"}},
        {"step": {"id": "listing"}, "draft": {"title": "Test item"}},
    ]
    fake_http.get.return_value = {}
    listing = MagicMock()
    listing.url = "https://es.wallapop.com/item/test-item-99"
    listing.web_slug = "test-item-99"
    with (
        patch("walla.account.sell.auth_client", return_value=fake_http),
        patch("walla.account.sell.post_step", side_effect=fake_http.post.side_effect),
        patch("walla.account.sell.poll_suggested", return_value=None),
        patch("walla.account.sell.upload_pictures", return_value=1),
        patch(
            "walla.account.sell.create_listing",
            return_value={"id": "abc123", "flags": {}},
        ),
        patch("walla.account.sell.get_item", return_value=listing),
    ):
        out = publish_listing(
            [photo],
            title="Test item",
            description="Desc",
            price_eur=12,
            category_leaf_id="10105",
            root_category_id="12579",
            lat=41.39,
            lon=2.17,
        )
    assert out["id"] == "abc123"
    assert out["photos"] == 1
    assert out["url"] == "https://es.wallapop.com/item/test-item-99"


def test_create_listing_multipart(tmp_path: Path) -> None:
    from walla.account.sell import create_listing

    photo = tmp_path / "a.jpg"
    photo.write_bytes(b"\xff\xd8\xff\xd9")
    item = build_item_body(
        upload_id="u",
        title="t",
        description="d",
        price_eur=9,
        category_leaf_id="10105",
        lat=41.0,
        lon=2.0,
    )
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {"id": "xyz", "flags": {}}
    fake_session = MagicMock()
    fake_session.request.return_value = fake_resp
    with (
        patch("walla.account.sell.auth_headers", return_value={"Authorization": "Bearer x"}),
        patch("walla.account.sell.requests.Session", return_value=fake_session),
        patch("walla.account.sell.CurlMime") as mime_cls,
        patch("walla.account.sell.wait_turn"),
    ):
        mime_cls.return_value = MagicMock()
        out = create_listing(item, photo)
    assert out["id"] == "xyz"


def test_delete_listing_mocked() -> None:
    from walla.account.sell import delete_listing

    http = MagicMock()
    out = delete_listing("abc", client=http)
    assert out == {"id": "abc", "deleted": True}
    http.delete.assert_called_once()


def test_publish_listing_two_photos(tmp_path: Path) -> None:
    from walla.account.sell import publish_listing
    from walla.core.exceptions import WallaHTTPError

    p1 = tmp_path / "a.jpg"
    p2 = tmp_path / "b.jpg"
    p1.write_bytes(b"\xff\xd8\xff\xd9")
    p2.write_bytes(b"\xff\xd8\xff\xd9")
    fake_http = MagicMock()
    fake_http.post.side_effect = [
        {"step": {"id": "title"}},
        {"step": {"id": "photo"}},
        {"step": {"id": "category"}},
        {"step": {"id": "loading"}},
        {"step": {"id": "listing"}},
    ]
    fake_http.get.side_effect = [
        WallaHTTPError("missing", status_code=404),
        {},
    ]
    fake_resp = MagicMock()
    fake_resp.status_code = 204
    fake_resp.text = ""
    fake_session = MagicMock()
    fake_session.request.return_value = fake_resp
    listing = MagicMock()
    listing.url = "https://es.wallapop.com/item/test-item-99"
    listing.web_slug = "test-item-99"
    with (
        patch("walla.account.sell.auth_client", return_value=fake_http),
        patch("walla.account.sell.post_step", side_effect=fake_http.post.side_effect),
        patch("walla.account.sell.poll_suggested", return_value=None),
        patch("walla.account.sell.upload_pictures", return_value=2),
        patch(
            "walla.account.sell.create_listing",
            return_value={"id": "abc123", "flags": {}},
        ),
        patch("walla.account.sell.get_item", return_value=listing),
        patch("walla.account.sell.auth_headers", return_value={}),
        patch("walla.account.sell.requests.Session", return_value=fake_session),
        patch("walla.account.sell.CurlMime") as mime_cls,
        patch("walla.account.sell.wait_turn"),
    ):
        mime_cls.return_value = MagicMock()
        out = publish_listing(
            [p1, p2],
            title="Test item",
            description="Desc",
            price_eur=12,
            category_leaf_id="10105",
            root_category_id="12579",
            lat=41.39,
            lon=2.17,
            shipping=True,
            weight_kg=2,
        )
    assert out["photos"] == 2
    assert out["url"] == "https://es.wallapop.com/item/test-item-99"
    fake_session.request.assert_called()


def test_public_item_url_uses_slug_not_hash() -> None:
    from walla.account.sell import _public_item_url

    listing = MagicMock()
    listing.url = ""
    listing.web_slug = "escritorio-madera-1309402890"
    with patch("walla.account.sell.get_item", return_value=listing):
        assert _public_item_url("x6qq0n82pe6y").endswith(
            "/item/escritorio-madera-1309402890"
        )
    with patch(
        "walla.account.sell.get_item",
        side_effect=WallaHTTPError("down", status_code=500),
    ):
        assert _public_item_url("x6qq0n82pe6y").endswith("/item/x6qq0n82pe6y")


def test_assert_item_body_errors() -> None:
    with pytest.raises(ValueError, match="missing"):
        assert_item_body({})
    with pytest.raises(ValueError, match="attributes"):
        assert_item_body(
            {
                "attributes": "nope",
                "category_leaf_id": "1",
                "apply_discount": False,
                "location": {"latitude": 1, "longitude": 2},
                "delivery": {},
                "upload_id": "u",
            }
        )
    with pytest.raises(ValueError, match="location"):
        assert_item_body(
            {
                "attributes": {"title": "t", "description": "d", "price_amount": 1},
                "category_leaf_id": "1",
                "apply_discount": False,
                "location": {},
                "delivery": {},
                "upload_id": "u",
            }
        )


def test_missing_shipping_weight() -> None:
    assert "shipping" in missing_sell_fields(
        {
            "title": "t",
            "description": "d",
            "eur": 1,
            "category_leaf_id": "1",
            "root_category_id": "2",
            "shipping": True,
        }
    )


def test_upload_pictures_requires_file(tmp_path: Path) -> None:
    from walla.account.sell import upload_pictures

    with pytest.raises(ValueError, match="at least one"):
        upload_pictures("uid", [])
    with pytest.raises(ValueError, match="photo not found"):
        from walla.account.sell import publish_listing

        publish_listing(
            [tmp_path / "missing.jpg"],
            title="t",
            description="d",
            price_eur=1,
            category_leaf_id="1",
            root_category_id="2",
            lat=1.0,
            lon=2.0,
        )
