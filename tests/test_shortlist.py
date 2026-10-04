"""Ranked shortlist helpers."""

from __future__ import annotations

from walla.hunter.shortlist import PRESENT_RULE, rank_shortlist


def test_rank_grab_before_look_and_cheaper_first() -> None:
    rows = [
        {
            "id": "look-cheap",
            "title": "Look cheap",
            "verdict": "LOOK",
            "price": {"amount": 200},
            "url": "https://es.wallapop.com/item/look-cheap",
            "location": {"city": "A"},
            "shippable": True,
        },
        {
            "id": "grab-dear",
            "title": "Grab dear",
            "verdict": "GRAB",
            "price": {"amount": 700},
            "url": "https://es.wallapop.com/item/grab-dear",
            "location": {"city": "B"},
            "user_allows_shipping": True,
        },
        {
            "id": "grab-cheap",
            "title": "Grab cheap",
            "verdict": "GRAB",
            "price": {"amount": 430},
            "url": "https://es.wallapop.com/item/grab-cheap",
            "location": {"city": "C"},
            "shippable": True,
        },
        {
            "id": "pass",
            "title": "Pass",
            "verdict": "PASS",
            "price": {"amount": 10},
            "url": "https://es.wallapop.com/item/pass",
        },
    ]
    ranked = rank_shortlist(rows)
    assert [r["id"] for r in ranked] == ["grab-cheap", "grab-dear", "look-cheap"]
    assert ranked[0]["rank"] == 1
    assert ranked[0]["url"].startswith("https://es.wallapop.com/item/")
    assert "Wallapop" in PRESENT_RULE
    assert "markdown" in PRESENT_RULE.lower()
