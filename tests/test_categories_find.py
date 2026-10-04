"""Category tree find / root resolve."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from walla.search.category_find import find_categories, flatten_categories, resolve_root_id
from walla.search.parse import parse_categories
from walla.search.pick_category import pick_sell_category

FIX = Path(__file__).resolve().parents[1] / "fixtures"


def _roots():
    raw = json.loads((FIX / "categories.json").read_text(encoding="utf-8"))
    return parse_categories(raw)


def test_parse_nested_categories() -> None:
    roots = _roots()
    hogar = next(c for c in roots if c.id == 12467)
    assert hogar.subcategories
    assert flatten_categories(roots)
    assert resolve_root_id(roots, "24208") == "12467"
    assert resolve_root_id(roots, "10105") == "12579"


def test_find_escritorio() -> None:
    hits = find_categories(_roots(), "escritorio")
    assert hits
    assert hits[0].leaf_id == "24208"
    assert hits[0].root_id == "12467"
    assert hits[0].is_leaf


def test_pick_by_name_and_id() -> None:
    roots = _roots()
    by_name = pick_sell_category(roots, category="escritorio")
    assert by_name.leaf_id == "24208"
    assert by_name.root_id == "12467"
    by_id = pick_sell_category(roots, category="24208")
    assert by_id.leaf_id == "24208"
    assert by_id.root_id == "12467"
    forced = pick_sell_category(roots, category="10105", root="12579")
    assert forced.root_id == "12579"


def test_find_empty_and_unknown() -> None:
    with pytest.raises(ValueError, match="empty"):
        find_categories(_roots(), "   ")
    assert find_categories(_roots(), "zzzz-no-such") == []
    with pytest.raises(ValueError, match="unknown"):
        resolve_root_id(_roots(), "999999")
    with pytest.raises(ValueError, match="no category matches"):
        pick_sell_category(_roots(), category="zzzz-no-such")
