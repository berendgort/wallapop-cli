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
from walla.account.chat import open_conversation
from walla.account.inbox import list_conversations, list_messages, send_message
from walla.account.login import login_cookie_text, login_cookies, whoami
from walla.account.prompt import interactive_login, session_summary
from walla.account.session_store import clear_session, load_session
from walla.cli.catch import run_cmd
from walla.core.exceptions import WallaAuthError
from walla.hunter.negotiate import draft_negotiation
from walla.hunter.profile_store import load_profile
from walla.search.api import get_item

__all__ = ("register",)


def register(app: typer.Typer) -> None:
    @app.command("login")
    def login_cmd(
        cookies: Path | None = typer.Option(None, "--cookies", help="cookies.txt / JSON export"),
        cookie: str | None = typer.Option(None, "--cookie", help="Raw session cookie value"),
        password: bool = typer.Option(
            False, "--password", help="Optional email/password prompt (often fails on MFA)"
        ),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        """Log in by pasting a browser session cookie (no .env)."""

        def _run() -> dict[str, Any]:
            if cookies is not None:
                sess = login_cookies(cookies)
            elif cookie:
                sess = login_cookie_text(cookie)
            elif json and not password:
                raise WallaAuthError(
                    "Non-interactive login needs --cookie '<value>' or --cookies <file>. "
                    "Or run without --json to paste interactively."
                )
            else:
                sess = interactive_login(password=password)
            return session_summary(sess)

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

    @app.command("chat")
    def chat_cmd(
        item_id: str = typer.Argument(...),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        """Open chat on a listing (same as the Chat button). Never sends text."""

        def _run() -> dict[str, Any]:
            return open_conversation(item_id)

        run_cmd(_run, as_json=json)

    @app.command("say")
    def say_cmd(
        target: str = typer.Argument(..., help="Item id or conversation hash"),
        text: str = typer.Argument(...),
        yes: bool = typer.Option(False, "--yes"),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        """Send chat text. Opens conversation first when given an item id."""

        def _run() -> dict[str, Any]:
            if not yes:
                return {
                    "needs_confirm": True,
                    "target": target,
                    "text": text,
                    "hint": "Re-run with --yes to send",
                }
            return send_message(target, text, confirm=True)

        run_cmd(_run, as_json=json)

    @app.command("negotiate")
    def negotiate_cmd(
        item_id: str = typer.Argument(...),
        seller: str | None = typer.Option(None, "--seller", help="Seller micro_name if known"),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        """Draft a win-win Spanish message + fair offer. Never sends."""

        def _run() -> dict[str, Any]:
            item = get_item(item_id)
            brief = draft_negotiation(item, load_profile(), seller_name=seller)
            return brief.model_dump(mode="json")

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
