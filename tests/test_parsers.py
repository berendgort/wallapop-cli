"""Parser tests against redacted fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from walla.search.parse import parse_categories, parse_item, parse_search

FIX = Path(__file__).resolve().parents[1] / "fixtures"


def test_parse_search_fixture() -> None:
    raw = json.loads((FIX / "search_bicicleta.json").read_text(encoding="utf-8"))
    result = parse_search(raw)
    assert result.count >= 1
    row = result.listings[0]
    assert row.id
    assert row.price.currency == "EUR"
    assert row.web_slug
    assert row.url.startswith("https://es.wallapop.com/item/")
    assert result.next_page


def test_parse_item_fixture() -> None:
    raw = json.loads((FIX / "item_detail.json").read_text(encoding="utf-8"))
    item = parse_item(raw)
    assert item.id
    assert item.title
    assert item.price.amount > 0


def test_parse_categories_fixture() -> None:
    raw = json.loads((FIX / "categories.json").read_text(encoding="utf-8"))
    cats = parse_categories(raw)
    assert len(cats) >= 1
    assert cats[0].id
    assert cats[0].name
