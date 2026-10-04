"""User-visible fix recipes (not system prompts)."""

from __future__ import annotations

from typing import Any

__all__ = (
    "cookie_export_fix",
)

_SESSION_COOKIE = "__Secure-next-auth.session-token"


def cookie_export_fix() -> dict[str, Any]:
    return {
        "title": "Paste Wallapop session cookie",
        "steps": [
            "Open https://es.wallapop.com and log in until you see your feed.",
            f"Copy cookie {_SESSION_COOKIE} (Cookie-Editor extension, or F12 -> "
            "Application/Storage -> Cookies -> es.wallapop.com -> copy Value).",
            "Run: walla login",
            "Paste the cookie Value (the long string), not the cookie name, then Enter.",
            "Agents: walla login --cookie '<value>' --json",
            "Never paste the cookie into a chat log.",
        ],
        "say_to_user": (
            f"Run `walla login`, then paste the Value of cookie "
            f"`{_SESSION_COOKIE}` from https://es.wallapop.com "
            "(Cookie-Editor, or DevTools -> Application -> Cookies)."
        ),
    }
