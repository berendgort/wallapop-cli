"""MCP entrypoints."""

from __future__ import annotations

__all__ = ("run", "run_http")


def run() -> None:
    from walla.mcp.server import build_server

    build_server().run()


def run_http() -> None:
    from walla.mcp.server import build_server

    build_server().run(transport="streamable-http", host="127.0.0.1", port=8000)
