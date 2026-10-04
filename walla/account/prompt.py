"""Interactive login helpers (cookie paste primary)."""

from __future__ import annotations

import getpass
from typing import Any

import typer

from walla.account.cookies import SESSION_COOKIE
from walla.account.login import login_cookie_text, login_password
from walla.core.exceptions import WallaAuthError
from walla.models.account import SessionData

__all__ = ("interactive_login", "session_summary")

_COOKIE_HOWTO = f"""
How to get your Wallapop session cookie
=======================================

1. Open Chrome/Firefox and go to:
     https://es.wallapop.com
2. Log in with your Wallapop account (until you see your feed).
3. Copy the cookie named exactly:
     {SESSION_COOKIE}

   Easiest (extension):
     - Install "Cookie-Editor" from the Chrome/Firefox store
     - Click the Cookie-Editor icon on es.wallapop.com
     - Find {SESSION_COOKIE}
     - Click Copy on its Value

   Or DevTools (no extension):
     - Press F12 -> Application (Chrome) or Storage (Firefox)
     - Cookies -> https://es.wallapop.com
     - Click {SESSION_COOKIE}
     - Double-click the Value cell -> Ctrl+C / Cmd+C

4. Easiest paste (avoids terminal truncation):
     - In Cookie-Editor, Export -> save as cookies.txt
     - Run:  walla login --cookies ~/Downloads/cookies.txt
   Or paste ONLY the Value (starts with eyJ...), one line, Enter.
   Cookie-Editor's name:"value" form is also OK.
   Do NOT paste your password. Do NOT share this cookie in chat.
""".strip()


def interactive_login(*, password: bool = False) -> SessionData:
    """Prompt for cookie paste, or email/password when ``password`` is True."""
    if password:
        return _prompt_password()
    return _prompt_cookie()


def _prompt_cookie() -> SessionData:
    typer.echo(_COOKIE_HOWTO)
    typer.echo("")
    raw = typer.prompt(f"Paste {SESSION_COOKIE} value (or cookies.txt path)").strip()
    if not raw:
        raise WallaAuthError("empty paste - copy the cookie Value, not the name")
    return login_cookie_text(raw)


def _prompt_password() -> SessionData:
    typer.echo(
        "Password login often fails (MFA). Prefer plain: walla login  (paste cookie)."
    )
    email = typer.prompt("email").strip()
    pw = getpass.getpass("password: ")
    try:
        return login_password(username=email, password=pw)
    except WallaAuthError:
        typer.echo("Password rejected. Falling back to cookie paste.")
        return _prompt_cookie()


def session_summary(sess: SessionData) -> dict[str, Any]:
    return {
        "authenticated": True,
        "has_access_token": bool(sess.access_token),
        "has_cookie": bool(sess.session_cookie),
        "user_id": sess.user_id,
        "micro_name": sess.micro_name,
    }
