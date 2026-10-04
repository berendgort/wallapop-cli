"""Buy and sell negotiation that sends on its own. The human only closes."""

from __future__ import annotations

from typing import Any

import typer

from walla.account.desk import run_desk, run_pursue
from walla.cli.catch import run_cmd

__all__ = ("register",)


def register(app: typer.Typer) -> None:
    @app.command("pursue")
    def pursue_cmd(
        keywords: str = typer.Argument(..., help="What to find and message"),
        wave: int = typer.Option(5, "--wave", help="How many new chats to open (max 15)"),
        local: bool = typer.Option(False, "--local", help="Skip listings outside profile.km"),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        """Search, message the best listings, and answer replies. Does not pay."""

        def _run() -> dict[str, Any]:
            return run_pursue(keywords, wave=wave, local=local)

        run_cmd(_run, as_json=json)

    @app.command("desk")
    def desk_cmd(json: bool = typer.Option(False, "--json")) -> None:
        """Read the inbox once, answer open threads, summarize the best price."""

        def _run() -> dict[str, Any]:
            return run_desk()

        run_cmd(_run, as_json=json)
