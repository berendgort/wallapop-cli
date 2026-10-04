"""Local record of listings walla is negotiating. No HTTP."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from walla.core.path import pursuits_path

__all__ = (
    "Pursuit",
    "PursuitStore",
    "drop_pursuit",
    "load_pursuits",
    "remember",
    "save_pursuits",
)

Side = Literal["buy", "sell"]
Status = Literal["open", "waiting", "converged", "walked"]


class Pursuit(BaseModel):
    item_id: str
    title: str
    url: str = ""
    side: Side = "buy"
    ask_eur: float
    offer_eur: float
    walk_away_eur: float
    query: str = ""
    status: Status = "open"
    agreed_eur: float | None = None
    why: str = ""
    nudges: int = 0


class PursuitStore(BaseModel):
    schema_version: int = 1
    pursuits: list[Pursuit] = Field(default_factory=list)


def load_pursuits(path: Path | None = None) -> PursuitStore:
    p = path or pursuits_path()
    if not p.is_file():
        return PursuitStore()
    return PursuitStore.model_validate(json.loads(p.read_text(encoding="utf-8")))


def save_pursuits(store: PursuitStore, path: Path | None = None) -> Path:
    p = path or pursuits_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(store.model_dump_json(indent=2), encoding="utf-8")
    return p


def remember(pursuit: Pursuit, path: Path | None = None) -> Pursuit:
    store = load_pursuits(path)
    rest = [row for row in store.pursuits if row.item_id != pursuit.item_id]
    save_pursuits(store.model_copy(update={"pursuits": [*rest, pursuit]}), path)
    return pursuit


def drop_pursuit(item_id: str, path: Path | None = None) -> None:
    store = load_pursuits(path)
    kept = [row for row in store.pursuits if row.item_id != item_id]
    save_pursuits(store.model_copy(update={"pursuits": kept}), path)
