"""Terminal brand mark for ``walla --help``."""

from __future__ import annotations

from rich.text import Text

from walla.cli.console import console

__all__ = ("print_banner",)

_BANNER_ROWS = (
    r" ██╗    ██╗ █████╗ ██╗     ██╗      █████╗ ",
    r" ██║    ██║██╔══██╗██║     ██║     ██╔══██╗",
    r" ██║ █╗ ██║███████║██║     ██║     ███████║",
    r" ██║███╗██║██╔══██║██║     ██║     ██╔══██║",
    r" ╚███╔███╔╝██║  ██║███████╗███████╗██║  ██║",
    r"  ╚══╝╚══╝ ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═╝",
)

_STYLE = "bold #A3E635"
_TAG = "italic #D9F99D"
_CREDIT = "#84CC16"


def print_banner() -> None:
    if not console.is_terminal:
        return
    console.print()
    for row in _BANNER_ROWS:
        console.print(Text(row, style=_STYLE))
    console.print(Text("  WALLA-CLI  ·  look · offer · talk", style=_TAG))
    console.print(Text("  Dr. Berend Gort  ·  www.berendgort.dev", style=_CREDIT))
    console.print()
