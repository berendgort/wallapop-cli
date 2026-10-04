"""Typer CLI -- agent-friendly Wallapop client."""

from __future__ import annotations

from typing import Any

import typer
from typer.core import TyperGroup

from walla.cli import cmd_account, cmd_desk, cmd_look, cmd_ops, cmd_sell
from walla.cli.banner import print_banner

__all__ = ("app", "cli")


class _WallaGroup(TyperGroup):
    def format_help(self, ctx: Any, formatter: Any) -> None:
        print_banner()
        super().format_help(ctx, formatter)


app = typer.Typer(
    name="walla",
    cls=_WallaGroup,
    help=(
        "Wallapop.es look · offer · talk · sell. "
        "Example ask: find a used kite near Barcelona under 400eur, "
        "message seller, offer if GRAB. "
        "Install: pipx install 'walla-cli[mcp]'. "
        "Recipe: walla instruct --json."
    ),
    no_args_is_help=True,
    add_completion=False,
)

cmd_ops.register(app)
cmd_look.register(app)
cmd_account.register(app)
cmd_sell.register(app)
cmd_desk.register(app)


def cli() -> None:
    app()


if __name__ == "__main__":
    cli()
