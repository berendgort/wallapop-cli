"""Edit owned listings (price / description / shipping)."""

from __future__ import annotations

from typing import Any

import typer

from walla.account.sell_edit import edit_listing
from walla.cli.catch import run_cmd
from walla.hunter.pursuits import Pursuit, load_pursuits, remember

__all__ = ("register",)


def register(app: typer.Typer) -> None:
    @app.command("edit")
    def edit_cmd(
        item_id: str = typer.Argument(..., help="Owned listing id"),
        title: str | None = typer.Option(None, "--title"),
        description: str | None = typer.Option(None, "--description", "--desc"),
        eur: float | None = typer.Option(None, "--eur", help="New asking price"),
        ship: bool | None = typer.Option(
            None, "--ship/--no-ship", help="Toggle Wallapop shipping"
        ),
        weight_kg: float | None = typer.Option(None, "--weight-kg"),
        floor: float | None = typer.Option(
            None, "--floor", help="Update desk walk-away EUR for this listing"
        ),
        yes: bool = typer.Option(False, "--yes", help="Apply edit for real"),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        """Update title, description, price, or shipping on an owned listing."""

        def _run() -> dict[str, Any]:
            if title is None and description is None and eur is None and ship is None:
                raise ValueError("Pass --title, --desc, --eur, and/or --ship")
            if not yes:
                return {
                    "status": "draft",
                    "id": item_id,
                    "fields": {
                        "title": title,
                        "description": description,
                        "eur": eur,
                        "shipping": ship,
                        "weight_kg": weight_kg,
                        "floor": floor,
                    },
                    "hint": "Review, then walla edit <id> … --yes",
                }
            edited = edit_listing(
                item_id,
                title=title,
                description=description,
                price_eur=eur,
                shipping=ship,
                weight_kg=weight_kg,
            )
            if floor is not None or eur is not None:
                _touch_floor(item_id, ask=eur, floor=floor)
            return {"status": "edited", **edited}

        run_cmd(_run, as_json=json)


def _touch_floor(item_id: str, *, ask: float | None, floor: float | None) -> None:
    for row in load_pursuits().pursuits:
        if row.item_id != item_id or row.side != "sell":
            continue
        ask_eur = float(ask) if ask is not None else row.ask_eur
        walk = float(floor) if floor is not None else row.walk_away_eur
        if ask is not None and floor is None:
            walk = min(walk, ask_eur)
        remember(
            Pursuit(
                item_id=row.item_id,
                title=row.title,
                url=row.url,
                side="sell",
                ask_eur=ask_eur,
                offer_eur=ask_eur,
                walk_away_eur=walk,
                query=row.query,
                status=row.status,
                why=row.why,
            )
        )
        return
