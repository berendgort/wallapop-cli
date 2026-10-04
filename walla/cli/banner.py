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

_PITCH = (
    "Turns Claude, GPT, or Cursor into a Wallapop helper that "
    "actually does the work for you. Drop a few photos and answer "
    "a couple of questions; the agent publishes. When buyers message, "
    "it reads the chats, replies, and negotiates down to your minimum "
    "price, then shows you the best deal. You only open the Wallapop "
    "app to accept. No typing chats. No babysitting the inbox."
)
_INSTALL = (
    "Install: pipx install 'walla-cli[mcp]'  "
    "https://pypi.org/project/walla-cli/"
)


def print_banner() -> None:
    """Always emit pitch + install (agents often have no TTY)."""
    if console.is_terminal:
        console.print()
        for row in _BANNER_ROWS:
            console.print(Text(row, style=_STYLE))
        console.print(Text("  look · offer · talk · sell", style=_TAG))
        console.print(Text("  Dr. Berend Gort  ·  www.berendgort.dev", style=_CREDIT))
        console.print()
        console.print(Text(f"  {_PITCH}", style=_HOOK))
        console.print(Text(f"  {_INSTALL}", style=_CREDIT))
        console.print()
        return
    # Non-TTY (agents/pipes): plain lines only, no box art.
    console.print("walla - look · offer · talk · sell")
    console.print(_PITCH)
    console.print(_INSTALL)
