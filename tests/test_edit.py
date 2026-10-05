"""Edit-item fixture + soft shortlist / HEIC prep."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from walla.account.sell_edit_wire import assert_edit_body, build_edit_body
from walla.account.sell_photos import prepare_sell_photos
from walla.http.sign import sign_request
from walla.hunter.shortlist import soft_shortlist

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "fixtures" / "edit_item_request.json"


def test_edit_fixture_matches_builder() -> None:
    meta = json.loads(FIX.read_text(encoding="utf-8"))
    example = meta["example"]
    assert_edit_body(example)
    body = build_edit_body(
        title=example["attributes"]["title"],
        description=example["attributes"]["description"],
        price_eur=float(example["attributes"]["price_amount"]),
        category_leaf_id=str(example["category_leaf_id"]),
        condition=example["attributes"]["condition"],
        lat=float(example["location"]["latitude"]),
        lon=float(example["location"]["longitude"]),
        pictures=list(example["pictures"]),
        shipping=False,
    )
    for key in meta["required_keys"]:
        assert key in body
    assert body["pictures"][0]["order"] == 0


def test_sign_request_stable() -> None:
    sig = sign_request(
        method="PUT",
        url="https://api.wallapop.com/api/v3/items/abc",
        timestamp_ms="1700000000000",
    )
    assert isinstance(sig, str) and len(sig) > 20


def test_soft_shortlist_mandate_fallback() -> None:
    rows = [
        {
            "id": "a",
            "title": "ski jacket",
            "verdict": "PASS",
            "price": {"amount": 50},
            "url": "https://es.wallapop.com/item/a",
        },
        {
            "id": "b",
            "title": "other",
            "verdict": "PASS",
            "price": {"amount": 40},
            "url": "https://es.wallapop.com/item/b",
        },
    ]
    hard, note = soft_shortlist(rows, must_match=["north", "reach"])
    assert hard
    assert note is not None
    assert note["mandate_emptied"] is True
    assert [r["id"] for r in hard] == ["b", "a"]


def test_prepare_rejects_unknown(tmp_path: Path) -> None:
    bad = tmp_path / "x.gif"
    bad.write_bytes(b"GIF")
    with pytest.raises(ValueError, match="unsupported"):
        prepare_sell_photos([bad])


def test_prepare_heic_uses_convert(tmp_path: Path) -> None:
    src = tmp_path / "shot.HEIC"
    src.write_bytes(b"heic")
    dest = tmp_path / "shot.jpg"

    def _fake_run(cmd: list[str], **_: object) -> MagicMock:
        dest.write_bytes(b"\xff\xd8\xff\xd9")
        return MagicMock(returncode=0, stderr="", stdout="")

    with (
        patch("walla.account.sell_photos.shutil.which", return_value="convert"),
        patch("walla.account.sell_photos.subprocess.run", side_effect=_fake_run),
    ):
        out = prepare_sell_photos([src])
    assert out == [dest]
