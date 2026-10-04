"""Search API with mocked HTTP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from walla.http.client import HttpClient
from walla.search.api import get_categories, get_item, search_listings

FIX = Path(__file__).resolve().parents[1] / "fixtures"


class FakeClient(HttpClient):
    def __init__(self, mapping: dict[str, Any]) -> None:
        super().__init__()
        self.mapping = mapping

    def request(self, method: str, path: str, **kwargs: Any) -> Any:  # type: ignore[override]
        for key, val in self.mapping.items():
            if key in path:
                return val
        raise AssertionError(f"unexpected {path}")


def test_search_listings_mocked() -> None:
    raw = json.loads((FIX / "search_bicicleta.json").read_text(encoding="utf-8"))
    # no next page so loop stops
    raw = {**raw, "meta": {"next_page": None}}
    client = FakeClient({"/api/v3/search": raw})
    result = search_listings(
        "bicicleta", latitude=41.39, longitude=2.17, max_results=10, client=client
    )
    assert result.count >= 1


def test_get_item_mocked() -> None:
    raw = json.loads((FIX / "item_detail.json").read_text(encoding="utf-8"))
    client = FakeClient({"/api/v3/items/": raw})
    item = get_item("pzpkpw831lj3", client=client)
    assert item.id


def test_categories_mocked() -> None:
    raw = json.loads((FIX / "categories.json").read_text(encoding="utf-8"))
    client = FakeClient({"/api/v3/categories": raw})
    cats = get_categories(client=client)
    assert cats
