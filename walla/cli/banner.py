"""Terminal brand mark for ``walla --help``."""

from __future__ import annotations

from rich.text import Text

from walla.cli.console import console

__all__ = ("print_banner",)

_BANNER_ROWS = (
    r"██╗    ██╗  █████╗  ██╗      ██╗       █████╗            ██████╗ ██╗      ██╗",
    r"██║    ██║ ██╔══██╗ ██║      ██║      ██╔══██╗          ██╔════╝ ██║      ██║",
    r"██║ █╗ ██║ ███████║ ██║      ██║      ███████║  █████╗  ██║      ██║      ██║",
    r"██║███╗██║ ██╔══██║ ██║      ██║      ██╔══██║  ╚════╝  ██║      ██║      ██║",
    r"╚███╔███╔╝ ██║  ██║ ███████╗ ███████╗ ██║  ██║          ╚██████╗ ███████╗ ██║",
    r" ╚══╝╚══╝  ╚═╝  ╚═╝ ╚══════╝ ╚══════╝ ╚═╝  ╚═╝           ╚══════╝ ╚══════╝ ╚═╝",
)

_STYLE = "bold #A3E635"
_TAG = "italic #D9F99D"
_CREDIT = "#84CC16"
_HOOK = "#BEF264"

_EXAMPLE = (
    'Example: "Find a used kite near Barcelona under 400eur, '
    'message the seller, offer if it is a GRAB."'
)
_INSTALL = (
    "Install: pipx install 'walla-cli[mcp]'  "
    "https://pypi.org/project/walla-cli/"
)


def print_banner() -> None:
    """Always emit example + install (agents often have no TTY)."""
    if console.is_terminal:
        console.print()
        for row in _BANNER_ROWS:
            console.print(Text(row, style=_STYLE))
        console.print(Text("  look · offer · talk", style=_TAG))
        console.print(Text("  Dr. Berend Gort  ·  www.berendgort.dev", style=_CREDIT))
        console.print()
        console.print(Text(f"  {_EXAMPLE}", style=_HOOK))
        console.print(Text(f"  {_INSTALL}", style=_CREDIT))
        console.print()
        return
    # Non-TTY (agents/pipes): plain lines only, no box art.
    console.print("walla - look · offer · talk")
    console.print(_EXAMPLE)
    console.print(_INSTALL)
