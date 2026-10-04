"""Sell / Vender: drop photos, answer questions, publish with --yes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from walla.account.sell import delete_listing, publish_listing
from walla.account.sell_suggest import suggest_from_photos
from walla.account.sell_wire import CONDITIONS, SELL_QUESTIONS, missing_sell_fields
from walla.cli.catch import run_cmd
from walla.hunter.profile_store import load_profile
from walla.hunter.pursuits import Pursuit, drop_pursuit, remember
from walla.search.api import get_categories
from walla.search.pick_category import pick_sell_category

__all__ = ("register",)


def register(app: typer.Typer) -> None:
    @app.command("sell")
    def sell_cmd(
        photos: list[Path] = typer.Argument(..., help="JPEG/PNG/WebP paths"),
        title: str | None = typer.Option(None, "--title"),
        description: str | None = typer.Option(None, "--description", "--desc"),
        eur: float | None = typer.Option(None, "--eur"),
        category: str | None = typer.Option(
            None, "--category", help="Leaf id or name (escritorio)"
        ),
        root: str | None = typer.Option(
            None, "--root", help="Root id (optional; derived from leaf)"
        ),
        condition: str = typer.Option("good", "--condition"),
        ship: bool = typer.Option(False, "--ship"),
        weight_kg: float | None = typer.Option(None, "--weight-kg"),
        floor: float | None = typer.Option(
            None, "--floor", help="Lowest EUR desk may accept from a buyer"
        ),
        suggest: bool = typer.Option(
            False,
            "--suggest",
            help="Prefill category via Wallapop steps (needs --title)",
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
            title_use = title
            leaf = category
            root_id = root
            picked = None
            suggested = None
            auto = bool(title) and not category and not yes
            if suggest or auto:
                if not title:
                    raise ValueError("--suggest needs --title")
                suggested = suggest_from_photos(
                    paths, title=title, root_category_id=root
                )
                if suggested.get("category_leaf_id"):
                    leaf = str(suggested["category_leaf_id"])
                    root_id = str(suggested.get("root_category_id") or "")
            if category:
                picked = pick_sell_category(
                    get_categories(), category=category, root=root
                )
                leaf = picked.leaf_id
                root_id = picked.root_id
            elif leaf and str(leaf).isdigit():
                picked = pick_sell_category(
                    get_categories(), category=str(leaf), root=root_id or root
                )
                leaf = picked.leaf_id
                root_id = picked.root_id
            fields: dict[str, Any] = {
                "title": title_use,
                "description": description,
                "eur": eur,
                "category_leaf_id": leaf,
                "root_category_id": root_id,
                "condition": condition,
                "shipping": ship,
                "weight_kg": weight_kg,
            }
            missing = missing_sell_fields(fields)
            profile = load_profile()
            questions = [q for q in SELL_QUESTIONS if q["id"] in missing]
            draft: dict[str, Any] = {
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
                    "walla sell … --title … --suggest prefills category from Wallapop."
                ),
            }
            if picked is not None:
                draft["category"] = {
                    "leaf_id": picked.leaf_id,
                    "root_id": picked.root_id,
                    "path": picked.path,
                }
            if suggested is not None:
                draft["suggested"] = suggested
            if not yes:
                return {"status": "draft", **draft}
            if missing:
                raise ValueError(
                    f"Cannot publish; still need: {', '.join(missing)}. "
                    "Answer those, then pass --yes."
                )
            if profile.lat is None or profile.lon is None:
                raise ValueError("Set location first: walla setup --lat … --lon …")
            assert title_use and description and eur is not None and leaf and root_id
            lowest = min(floor, eur) if floor is not None else eur
            created = publish_listing(
                paths,
                title=title_use,
                description=description,
                price_eur=eur,
                category_leaf_id=str(leaf),
                root_category_id=str(root_id),
                lat=profile.lat,
                lon=profile.lon,
                condition=condition,
                shipping=ship,
                weight_kg=weight_kg,
            )
            remember(
                Pursuit(
                    item_id=str(created["id"]),
                    title=title_use,
                    url=str(created.get("url") or ""),
                    side="sell",
                    ask_eur=eur,
                    offer_eur=eur,
                    walk_away_eur=lowest,
                    query=title_use,
                    status="waiting",
                    why="Listing is live. Desk talks to buyers. You accept in the app.",
                )
            )
            return {
                "status": "published",
                "floor_eur": lowest,
                "category": draft.get("category"),
                **created,
            }

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
