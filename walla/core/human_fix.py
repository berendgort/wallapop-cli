"""User-visible fix recipes (not system prompts)."""

from __future__ import annotations

from typing import Any

__all__ = (
    "cookie_export_fix",
)


def cookie_export_fix() -> dict[str, Any]:
    return {
        "title": "Export Wallapop session cookie",
        "steps": [
            "Log in at https://es.wallapop.com in your browser.",
            "Export cookies for wallapop.com (Cookie-Editor / cookies.txt).",
            "Need cookie: __Secure-next-auth.session-token",
            "Run: walla login --cookies ~/Downloads/cookies.txt --json",
        ],
        "say_to_user": (
            "Password login was rejected (MFA or Keycloak). Export the "
            "__Secure-next-auth.session-token cookie and run "
            "`walla login --cookies <file>`."
        ),
    }
