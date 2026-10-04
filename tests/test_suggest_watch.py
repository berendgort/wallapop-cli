"""Suggest draft parse + desk watch stop conditions."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from walla.account.desk_watch import run_desk_watch
from walla.account.sell_steps import parse_steps_draft

FIX = Path(__file__).resolve().parents[1] / "fixtures"


def test_parse_steps_draft_fixture() -> None:
    raw = json.loads((FIX / "sell_suggest_draft.json").read_text(encoding="utf-8"))
    after = parse_steps_draft(raw["after_photo"])
    assert after["category_leaf_id"] == "24208"
    assert after["title"].startswith("Escritorio")
    loaded = parse_steps_draft(raw["after_loading"])
    assert loaded["root_category_id"] == "12467"


def test_desk_watch_stops_on_converged() -> None:
    converged = {
        "replies": [],
        "stack": {"best": {"status": "converged", "title": "X", "agreed_eur": 40}},
        "close_in_app": True,
    }
    with patch("walla.account.desk_watch.run_desk", return_value=converged) as desk:
        with patch("walla.account.desk_watch.time.sleep") as slept:
            out = run_desk_watch(seconds=5, rounds=5)
    assert out["watch_stopped"] == "converged"
    assert out["watch_round"] == 1
    desk.assert_called_once()
    slept.assert_not_called()


def test_desk_watch_max_rounds() -> None:
    waiting = {
        "replies": [],
        "stack": {"best": None},
        "close_in_app": True,
    }
    with patch("walla.account.desk_watch.run_desk", return_value=waiting) as desk:
        with patch("walla.account.desk_watch.time.sleep") as slept:
            out = run_desk_watch(seconds=5, rounds=3)
    assert out["watch_stopped"] == "max_rounds"
    assert out["watch_round"] == 3
    assert desk.call_count == 3
    assert slept.call_count == 2


def test_suggest_from_photos_mocked(tmp_path: Path) -> None:
    from walla.account.sell_suggest import suggest_from_photos

    photo = tmp_path / "a.jpg"
    photo.write_bytes(b"\xff\xd8\xff\xd9")
    steps = [
        {"step": {"id": "title"}, "draft": {}},
        {"step": {"id": "photo"}, "draft": {"title": "Escritorio madera"}},
        {
            "step": {"id": "category"},
            "draft": {"title": "Escritorio madera", "category_leaf_id": "24208"},
        },
        {
            "step": {"id": "loading"},
            "draft": {
                "title": "Escritorio madera",
                "category_leaf_id": "24208",
                "root_category_id": "12467",
            },
        },
        {
            "step": {"id": "listing"},
            "draft": {
                "title": "Escritorio madera",
                "category_leaf_id": "24208",
                "root_category_id": "12467",
            },
        },
    ]
    fake = MagicMock()
    with (
        patch("walla.account.sell_suggest.auth_client", return_value=fake),
        patch("walla.account.sell_suggest.post_step", side_effect=steps),
        patch("walla.account.sell_suggest.upload_pictures", return_value=1),
        patch("walla.account.sell_suggest.poll_suggested", return_value=None),
        patch(
            "walla.account.sell_suggest.get_categories",
            return_value=__import__(
                "walla.search.parse", fromlist=["parse_categories"]
            ).parse_categories(
                json.loads((FIX / "categories.json").read_text(encoding="utf-8"))
            ),
        ),
    ):
        out = suggest_from_photos([photo], title="Escritorio madera")
    assert out["category_leaf_id"] == "24208"
    assert out["root_category_id"] == "12467"
    assert "Escritorios" in (out.get("path") or "")
