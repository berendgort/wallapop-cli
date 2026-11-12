"""Interactive login helpers (cookie paste primary)."""

from __future__ import annotations

import getpass
import shutil
import subprocess
import sys
from typing import Any

import typer

from walla.account.cookies import SESSION_COOKIE
from walla.account.login import login_cookie_text, login_password
from walla.core.exceptions import WallaAuthError
from walla.models.account import SessionData

__all__ = ("interactive_login", "session_summary")

_COOKIE_HOWTO = f"""
Wallapop login
  1. es.wallapop.com, logged in -> Cookie-Editor (or F12 -> Application -> Cookies)
  2. Copy the Value of {SESSION_COOKIE}
  3. Run walla login again, or paste below (hidden, Enter to finish)
""".strip()


def interactive_login(*, password: bool = False) -> SessionData:
    """Prompt for cookie paste, or email/password when ``password`` is True."""
    if password:
        return _prompt_password()
    return _prompt_cookie()


def _prompt_cookie() -> SessionData:
    raw = _clipboard_cookie()
    if raw:
        typer.echo("Using the session cookie from your clipboard.")
    else:
        typer.echo(_COOKIE_HOWTO)
        raw = _read_hidden("Cookie: ").strip()
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


def _clipboard_cookie() -> str:
    """Cookie text from the clipboard, or '' when it does not look like one."""
    for cmd in (["wl-paste", "-n"], ["xclip", "-o", "-sel", "clip"], ["pbpaste"]):
        if not shutil.which(cmd[0]):
            continue
        try:
            text = subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            continue
        if text.startswith("eyJ") or SESSION_COOKIE in text:
            return text
    return ""


def _read_hidden(prompt: str) -> str:
    """No-echo line read. getpass would cut at the 4096-char tty line limit; cookies are longer."""
    if not sys.stdin.isatty():
        return sys.stdin.readline()
    import termios

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    new = termios.tcgetattr(fd)
    new[3] &= ~(termios.ECHO | termios.ICANON)
    sys.stderr.write(prompt)
    sys.stderr.flush()
    chars: list[str] = []
    try:
        termios.tcsetattr(fd, termios.TCSADRAIN, new)
        while (ch := sys.stdin.read(1)) not in ("\n", "\r", ""):
            chars.append(ch)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stderr.write("\n")
    return "".join(chars)


def session_summary(sess: SessionData) -> dict[str, Any]:
    return {
        "authenticated": True,
        "has_access_token": bool(sess.access_token),
        "has_cookie": bool(sess.session_cookie),
        "user_id": sess.user_id,
        "micro_name": sess.micro_name,
    }
