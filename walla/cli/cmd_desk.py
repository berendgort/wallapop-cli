"""Buy and sell negotiation that sends on its own. The human only closes."""

from __future__ import annotations

from typing import Any

import typer

from walla.account.desk import run_desk, run_pursue
from walla.account.desk_watch import run_desk_watch
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
    def desk_cmd(
        watch: bool = typer.Option(
            False, "--watch", help="Poll inbox until a price converges"
        ),
        seconds: float = typer.Option(45.0, "--seconds", help="Sleep between watch rounds"),
        rounds: int = typer.Option(12, "--rounds", help="Max watch rounds (1..60)"),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        """Read the inbox, answer open threads, summarize the best price."""

        def _run() -> dict[str, Any]:
            if watch:
                return run_desk_watch(seconds=seconds, rounds=rounds)
            return run_desk()

        run_cmd(_run, as_json=json)
