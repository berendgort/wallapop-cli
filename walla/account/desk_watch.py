"""Poll the inbox until a deal converges or rounds run out."""

from __future__ import annotations

import time
from typing import Any

from walla.account.desk import run_desk
from walla.http.client import HttpClient

__all__ = ("run_desk_watch",)


def run_desk_watch(
    *,
    seconds: float = 45.0,
    rounds: int = 12,
    client: HttpClient | None = None,
) -> dict[str, Any]:
    """Repeat run_desk until stack.best is converged or max rounds."""
    if seconds < 5:
        raise ValueError("--seconds must be >= 5")
    if rounds < 1 or rounds > 60:
        raise ValueError("--rounds must be 1..60")
    last: dict[str, Any] = {}
    for i in range(rounds):
        last = run_desk(client=client)
        last["watch_round"] = i + 1
        best = (last.get("stack") or {}).get("best")
        if isinstance(best, dict) and best.get("status") == "converged":
            last["watch_stopped"] = "converged"
            return last
        if i + 1 < rounds:
            time.sleep(float(seconds))
    last["watch_stopped"] = "max_rounds"
    return last
