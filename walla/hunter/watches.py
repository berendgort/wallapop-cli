"""Local saved searches with new-id diff."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from walla.core.path import watches_path

__all__ = (
    "Watch",
    "WatchStore",
    "diff_new_ids",
    "load_watches",
    "save_watches",
)


class Watch(BaseModel):
    id: str
    keywords: str
    max_price: float | None = None
    category_id: int | None = None
    seen_ids: list[str] = Field(default_factory=list)


class WatchStore(BaseModel):
    schema_version: int = 1
    watches: list[Watch] = Field(default_factory=list)


def load_watches(path: Path | None = None) -> WatchStore:
    p = path or watches_path()
    if not p.is_file():
        return WatchStore()
    return WatchStore.model_validate(json.loads(p.read_text(encoding="utf-8")))


def save_watches(store: WatchStore, path: Path | None = None) -> Path:
    p = path or watches_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(store.model_dump_json(indent=2), encoding="utf-8")
    return p


def diff_new_ids(seen: list[str], found: list[str]) -> list[str]:
    known = set(seen)
    return [i for i in found if i not in known]


def merge_seen(watch: Watch, found_ids: list[str]) -> Watch:
    merged = list(dict.fromkeys([*watch.seen_ids, *found_ids]))
    return watch.model_copy(update={"seen_ids": merged})


def watch_to_dict(watch: Watch) -> dict[str, Any]:
    return watch.model_dump(mode="json")
