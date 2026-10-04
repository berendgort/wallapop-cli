"""CLI error catching and JSON envelope printing."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, TypeVar

import typer

from walla.cli.console import console
from walla.core.envelope import error_payload, success_payload

__all__ = (
    "emit",
    "run_cmd",
)

F = TypeVar("F", bound=Callable[..., Any])


def emit(payload: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        console.print_json(json.dumps(payload, ensure_ascii=False))
    else:
        if payload.get("ok"):
            data = payload.get("data")
            console.print(data)
        else:
            console.print(f"[red]{payload.get('error')}[/red]")
            raise typer.Exit(code=1)


def run_cmd(fn: Callable[[], Any], *, as_json: bool) -> None:
    try:
        data = fn()
        emit(success_payload(data), as_json=as_json)
    except Exception as exc:  # noqa: BLE001
        emit(error_payload(exc), as_json=True if as_json else as_json)
        if as_json:
            raise typer.Exit(code=1) from exc
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
