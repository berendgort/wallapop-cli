"""Park a redacted agent transcript locally."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from walla.cli.catch import run_cmd
from walla.core.teach import park_transcript
from walla.core.teach_pr import ship_pr

__all__ = ("register",)


def register(app: typer.Typer) -> None:
    @app.command("teach")
    def teach_cmd(
        source: Path | None = typer.Argument(
            None,
            help="Transcript file, or - for stdin",
        ),
        name: str | None = typer.Option(None, "--name", help="Filename stem"),
        method: str | None = typer.Option(
            None,
            "--method",
            help="PR path: a=gh b=git c=browser d=hub e=manual",
        ),
        yes: bool = typer.Option(False, "--yes", help="Open/push the PR for real"),
        json: bool = typer.Option(False, "--json"),
    ) -> None:
        """Park a redacted transcript; --method a-e opens a GitHub PR."""

        def _run() -> dict[str, Any]:
            if source is None:
                raise ValueError("Pass a file, or pipe stdin: walla teach - < chat.md")
            if str(source) == "-":
                text = typer.get_text_stream("stdin").read()
                stem = name or "stdin"
            else:
                path = source.expanduser()
                if not path.is_file():
                    raise ValueError(f"transcript not found: {path}")
                text = path.read_text(encoding="utf-8")
                stem = name or path.stem
            parked = park_transcript(text, name=stem)
            out: dict[str, Any] = {"status": "parked", **parked}
            if method:
                out["pr"] = ship_pr(Path(str(parked["path"])), method=method, yes=yes)
            return out

        run_cmd(_run, as_json=json)
