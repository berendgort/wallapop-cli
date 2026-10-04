"""Account commands: login, inbox, say, offer, fav."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from walla.account.actions import (
    add_favorite,
    list_favorites,
    make_offer,
    quote_offer,
    remove_favorite,
)
from walla.account.inbox import list_conversations, list_messages, send_message
from walla.account.login import login_cookies, login_password, whoami
from walla.account.session_store import clear_session, load_session
from walla.cli.catch import run_cmd
from walla.search.api import get_item

__all__ = ("register",)


def register(app: typer.Typer) -> None:
    @app.command("login")
    def login_cmd(
        cookies: Path | None = typer.Option(None, "--cookies"),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        def _run() -> dict[str, Any]:
            if cookies:
                sess = login_cookies(cookies)
            else:
                sess = login_password()
            return {
                "authenticated": True,
                "has_access_token": bool(sess.access_token),
                "has_cookie": bool(sess.session_cookie),
                "user_id": sess.user_id,
                "micro_name": sess.micro_name,
            }

        run_cmd(_run, as_json=json)

    @app.command("logout")
    def logout_cmd(json: bool = typer.Option(False, "--json")) -> None:
        def _run() -> dict[str, Any]:
            clear_session()
            return {"authenticated": False}

        run_cmd(_run, as_json=json)

    @app.command("whoami")
    def whoami_cmd(json: bool = typer.Option(False, "--json")) -> None:
        run_cmd(lambda: whoami(), as_json=json)

    @app.command("inbox")
    def inbox_cmd(json: bool = typer.Option(False, "--json")) -> None:
        def _run() -> dict[str, Any]:
            rows = list_conversations()
            return {"conversations": [c.model_dump(mode="json") for c in rows]}

        run_cmd(_run, as_json=json)

    @app.command("thread")
    def thread_cmd(
        conversation_id: str = typer.Argument(...),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        def _run() -> dict[str, Any]:
            msgs = list_messages(conversation_id)
            return {
                "conversation_id": conversation_id,
                "messages": [m.model_dump(mode="json") for m in msgs],
            }

        run_cmd(_run, as_json=json)

    @app.command("say")
    def say_cmd(
        conversation_id: str = typer.Argument(...),
        text: str = typer.Argument(...),
        yes: bool = typer.Option(False, "--yes"),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        def _run() -> dict[str, Any]:
            return send_message(conversation_id, text, confirm=yes)

        run_cmd(_run, as_json=json)

    @app.command("offer")
    def offer_cmd(
        item_id: str = typer.Argument(...),
        eur: float = typer.Option(..., "--eur"),
        yes: bool = typer.Option(False, "--yes"),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        def _run() -> dict[str, Any]:
            if not yes:
                item = get_item(item_id)
                quote = quote_offer(item, eur)
                return {
                    "needs_confirm": True,
                    "title": item.title,
                    "url": item.url,
                    "quote": quote.model_dump(mode="json"),
                    "hint": "Re-run with --yes to send",
                }
            return make_offer(item_id, eur, confirm=True)

        run_cmd(_run, as_json=json)

    fav_app = typer.Typer(help="Favorites")
    app.add_typer(fav_app, name="fav")

    @fav_app.command("list")
    def fav_list(json: bool = typer.Option(False, "--json")) -> None:
        def _run() -> dict[str, Any]:
            return {"favorites": list_favorites()}

        run_cmd(_run, as_json=json)

    @fav_app.command("add")
    def fav_add(
        item_id: str = typer.Argument(...),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        run_cmd(lambda: add_favorite(item_id), as_json=json)

    @fav_app.command("rm")
    def fav_rm(
        item_id: str = typer.Argument(...),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        run_cmd(lambda: remove_favorite(item_id), as_json=json)

    @app.command("session")
    def session_cmd(json: bool = typer.Option(False, "--json")) -> None:
        def _run() -> dict[str, Any]:
            sess = load_session()
            if not sess:
                return {"authenticated": False}
            return {
                "authenticated": True,
                "has_access_token": bool(sess.access_token),
                "has_cookie": bool(sess.session_cookie),
                "user_id": sess.user_id,
                "micro_name": sess.micro_name,
            }

        run_cmd(_run, as_json=json)
