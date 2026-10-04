"""Sell / Vender: drop photos, answer questions, publish with --yes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from walla.account.sell import delete_listing, publish_listing
from walla.account.sell_wire import CONDITIONS, SELL_QUESTIONS, missing_sell_fields
from walla.cli.catch import run_cmd
from walla.hunter.profile_store import load_profile
from walla.hunter.pursuits import Pursuit, drop_pursuit, remember

__all__ = ("register",)


def register(app: typer.Typer) -> None:
    @app.command("sell")
    def sell_cmd(
        photos: list[Path] = typer.Argument(..., help="JPEG/PNG/WebP paths"),
        title: str | None = typer.Option(None, "--title"),
        description: str | None = typer.Option(None, "--description", "--desc"),
        eur: float | None = typer.Option(None, "--eur"),
        category: str | None = typer.Option(None, "--category", help="Leaf category id"),
        root: str | None = typer.Option(None, "--root", help="Root category id"),
        condition: str = typer.Option("good", "--condition"),
        ship: bool = typer.Option(False, "--ship"),
        weight_kg: float | None = typer.Option(None, "--weight-kg"),
        floor: float | None = typer.Option(
            None, "--floor", help="Lowest EUR desk may accept from a buyer"
        ),
        yes: bool = typer.Option(False, "--yes", help="Publish for real"),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        """Draft or publish a consumer-goods listing from photos (Vender)."""

        def _run() -> dict[str, Any]:
            paths = [p.expanduser() for p in photos]
            for p in paths:
                if not p.is_file():
                    raise ValueError(f"photo not found: {p}")
            fields: dict[str, Any] = {
                "title": title,
                "description": description,
                "eur": eur,
                "category_leaf_id": category,
                "root_category_id": root,
                "condition": condition,
                "shipping": ship,
                "weight_kg": weight_kg,
            }
            missing = missing_sell_fields(fields)
            profile = load_profile()
            questions = [q for q in SELL_QUESTIONS if q["id"] in missing]
            draft = {
                "photos": [str(p) for p in paths],
                "fields": fields,
                "missing": missing,
                "questions": questions,
                "conditions": list(CONDITIONS),
                "location": {
                    "lat": profile.lat,
                    "lon": profile.lon,
                    "label": profile.label,
                },
                "hint": (
                    "Fill missing fields, then walla sell <photos> … --yes. "
                    "Pick category ids via walla categories --json."
                ),
            }
            if not yes:
                return {"status": "draft", **draft}
            if missing:
                raise ValueError(
                    f"Cannot publish; still need: {', '.join(missing)}. "
                    "Answer those, then pass --yes."
                )
            if profile.lat is None or profile.lon is None:
                raise ValueError("Set location first: walla setup --lat … --lon …")
            assert title and description and eur is not None and category and root
            lowest = min(floor, eur) if floor is not None else eur
            created = publish_listing(
                paths,
                title=title,
                description=description,
                price_eur=eur,
                category_leaf_id=category,
                root_category_id=root,
                lat=profile.lat,
                lon=profile.lon,
                condition=condition,
                shipping=ship,
                weight_kg=weight_kg,
            )
            remember(
                Pursuit(
                    item_id=str(created["id"]),
                    title=title,
                    url=str(created.get("url") or ""),
                    side="sell",
                    ask_eur=eur,
                    offer_eur=eur,
                    walk_away_eur=lowest,
                    query=title,
                    status="waiting",
                    why="Listing is live. Desk talks to buyers. You accept in the app.",
                )
            )
            return {"status": "published", "floor_eur": lowest, **created}

        run_cmd(_run, as_json=json)

    @app.command("unsell")
    def unsell_cmd(
        item_id: str = typer.Argument(...),
        yes: bool = typer.Option(False, "--yes"),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        """Delete one of your listings (DELETE /api/v3/items/{id})."""

        def _run() -> dict[str, Any]:
            if not yes:
                raise ValueError("Refusing delete without --yes")
            deleted = delete_listing(item_id)
            drop_pursuit(item_id)
            return deleted

        run_cmd(_run, as_json=json)
