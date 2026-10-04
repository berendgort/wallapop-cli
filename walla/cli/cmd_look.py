"""Look commands: search, item, categories, watch, export."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import typer

from walla.cli.catch import run_cmd
from walla.hunter.export import load_last_search, save_last_search, write_exports
from walla.hunter.profile_store import load_profile
from walla.hunter.shortlist import PRESENT_RULE, rank_shortlist
from walla.hunter.verdict import geo_scope, score_listing
from walla.hunter.watches import (
    Watch,
    diff_new_ids,
    load_watches,
    merge_seen,
    save_watches,
)
from walla.search.api import get_categories, get_item, search_listings

__all__ = ("register",)


def register(app: typer.Typer) -> None:
    @app.command("search")
    def search(
        keywords: str = typer.Argument(...),
        max_results: int = typer.Option(40, "--max"),
        min_price: float | None = typer.Option(None, "--min"),
        max_price: float | None = typer.Option(None, "--max-price"),
        category_id: int | None = typer.Option(None, "--category"),
        order_by: str = typer.Option("most_relevance", "--order"),
        local: bool = typer.Option(
            False, "--local", help="PASS listings outside profile.km"
        ),
        export: str | None = typer.Option(
            None, "--export", help="Formats: md,csv,html,pdf"
        ),
        out: Path | None = typer.Option(None, "--out", help="Export directory"),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        def _run() -> dict[str, Any]:
            profile = load_profile()
            if not profile.ready:
                return {
                    "ready": False,
                    "intake": {"prompt_to_user": profile.intake_prompt()},
                }
            result = search_listings(
                keywords,
                latitude=float(profile.lat or 0),
                longitude=float(profile.lon or 0),
                max_results=max_results,
                min_price=min_price,
                max_price=max_price or profile.budget,
                category_id=category_id,
                order_by=order_by,
            )
            rows = []
            for listing in result.listings:
                listing.verdict = score_listing(listing, profile, local=local)
                rows.append(listing.model_dump(mode="json"))
            mandate = {
                "budget": profile.spend_cap,
                "aggressiveness": profile.aggressiveness,
                "must_match": profile.must_match,
            }
            save_last_search(keywords=keywords, listings=rows, mandate=mandate)
            shortlist = rank_shortlist(rows)
            payload: dict[str, Any] = {
                "count": len(rows),
                "next_page": result.next_page,
                "listings": rows,
                "shortlist": shortlist,
                "geo": geo_scope(local=local),
                "mandate": mandate,
                "source": "wallapop.es",
                "hitl": {
                    "grabs": sum(1 for r in rows if r.get("verdict") == "GRAB"),
                    "ask_if_multiple_grabs": True,
                    "present": PRESENT_RULE,
                    "next": (
                        "Show shortlist with markdown links (data.shortlist). "
                        "If one GRAB: walla negotiate <id> --json. "
                        "If several: ask human to pick an id. Never pay."
                    ),
                },
            }
            if export:
                payload["exported"] = write_exports(
                    rows,
                    profile,
                    formats=[p.strip() for p in export.split(",")],
                    out_dir=out or Path.cwd(),
                    keywords=keywords,
                )
            return payload

        run_cmd(_run, as_json=json)

    @app.command("export")
    def export_cmd(
        format: str = typer.Option(
            "md,csv,html,pdf", "--format", help="md,csv,html,pdf"
        ),
        out: Path | None = typer.Option(None, "--out", help="Output directory"),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        """Export the last search shortlist (no network)."""

        def _run() -> dict[str, Any]:
            data = load_last_search()
            profile = load_profile()
            written = write_exports(
                list(data.get("listings") or []),
                profile,
                formats=[p.strip() for p in format.split(",")],
                out_dir=out or Path.cwd(),
                keywords=str(data.get("keywords") or ""),
            )
            return {
                "keywords": data.get("keywords"),
                "count": len(data.get("listings") or []),
                "exported": written,
            }

        run_cmd(_run, as_json=json)

    @app.command("item")
    def item_cmd(
        item_id: str = typer.Argument(...),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        def _run() -> dict[str, Any]:
            listing = get_item(item_id)
            profile = load_profile()
            listing.verdict = score_listing(listing, profile)
            return listing.model_dump(mode="json")

        run_cmd(_run, as_json=json)

    @app.command("categories")
    def categories_cmd(json: bool = typer.Option(False, "--json")) -> None:
        def _run() -> dict[str, Any]:
            cats = get_categories()
            return {"categories": [c.model_dump(mode="json") for c in cats]}

        run_cmd(_run, as_json=json)

    watch_app = typer.Typer(help="Local saved searches")
    app.add_typer(watch_app, name="watch")

    @watch_app.command("add")
    def watch_add(
        keywords: str = typer.Argument(...),
        max_price: float | None = typer.Option(None, "--max-price"),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        def _run() -> dict[str, Any]:
            store = load_watches()
            w = Watch(id=str(uuid.uuid4())[:8], keywords=keywords, max_price=max_price)
            store.watches.append(w)
            save_watches(store)
            return w.model_dump(mode="json")

        run_cmd(_run, as_json=json)

    @watch_app.command("list")
    def watch_list(json: bool = typer.Option(False, "--json")) -> None:
        def _run() -> dict[str, Any]:
            store = load_watches()
            return {"watches": [w.model_dump(mode="json") for w in store.watches]}

        run_cmd(_run, as_json=json)

    @watch_app.command("check")
    def watch_check(
        watch_id: str = typer.Argument(...),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        def _run() -> dict[str, Any]:
            store = load_watches()
            watch = next((w for w in store.watches if w.id == watch_id), None)
            if watch is None:
                raise ValueError(f"unknown watch {watch_id}")
            profile = load_profile()
            if not profile.ready:
                raise ValueError("profile not ready; run walla setup")
            result = search_listings(
                watch.keywords,
                latitude=float(profile.lat or 0),
                longitude=float(profile.lon or 0),
                max_results=40,
                max_price=watch.max_price,
            )
            found = [L.id for L in result.listings]
            new_ids = diff_new_ids(watch.seen_ids, found)
            store.watches = [
                merge_seen(w, found) if w.id == watch_id else w for w in store.watches
            ]
            save_watches(store)
            new_listings = [
                L.model_dump(mode="json") for L in result.listings if L.id in set(new_ids)
            ]
            return {"watch_id": watch_id, "new_ids": new_ids, "listings": new_listings}

        run_cmd(_run, as_json=json)
