"""Parse browser cookie exports for NextAuth session."""

from __future__ import annotations

import json
from pathlib import Path

from walla.core.exceptions import WallaAuthError

__all__ = (
    "SESSION_COOKIE",
    "parse_cookie_export",
    "parse_cookie_text",
)

SESSION_COOKIE = "__Secure-next-auth.session-token"


def parse_cookie_export(path: Path) -> tuple[str, str | None]:
    """Return (session_cookie, device_id) from a cookies file."""
    return parse_cookie_text(path.read_text(encoding="utf-8"))


def parse_cookie_text(text: str) -> tuple[str, str | None]:
    """Return (session_cookie, device_id) from pasted text or export body."""
    stripped = text.strip()
    if not stripped:
        raise WallaAuthError(f"empty cookie paste; need {SESSION_COOKIE}")
    if stripped.startswith("[") or stripped.startswith("{"):
        return _from_json(stripped)
    return _from_text(stripped)


def _from_json(text: str) -> tuple[str, str | None]:
    data = json.loads(text)
    session: str | None = None
    device: str | None = None
    rows = data if isinstance(data, list) else [data]
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("name") or row.get("Name")
        value = row.get("value") or row.get("Value")
        if name == SESSION_COOKIE and value:
            session = str(value)
        if name == "device_id" and value:
            device = str(value)
    if not session:
        raise WallaAuthError(f"no {SESSION_COOKIE} in JSON cookie export")
    return session, device


def _from_text(text: str) -> tuple[str, str | None]:
    session: str | None = None
    device: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or (line.startswith("#") and "HttpOnly" not in line):
            continue
        if line.startswith("#HttpOnly_"):
            line = line[len("#HttpOnly_") :]
        if "\t" in line:
            fields = line.split("\t")
            if len(fields) >= 7:
                name, value = fields[5], fields[6]
                if name == SESSION_COOKIE:
                    session = _strip_quotes(value)
                elif name == "device_id":
                    device = _strip_quotes(value)
            continue
        line = line.removeprefix("Cookie:").strip()
        # Cookie-Editor sometimes copies: name:"value" or name=value
        if SESSION_COOKIE in line and (":" in line or "=" in line):
            extracted = _extract_named(line, SESSION_COOKIE)
            if extracted:
                session = extracted
                continue
        for pair in line.split(";"):
            pair = pair.strip()
            if "=" not in pair and ":" not in pair:
                if pair.count(".") >= 2 and len(pair) > 100:
                    session = _strip_quotes(pair)
                continue
            name, value = _split_pair(pair)
            if name == SESSION_COOKIE:
                session = value
            elif name == "device_id":
                device = value
    if not session and text.count(".") >= 2 and len(text.strip()) > 100:
        candidate = _strip_quotes(text.strip())
        # Never treat howto text / multi-word junk as the cookie value.
        if " " not in candidate and "\t" not in candidate and candidate.startswith("eyJ"):
            session = candidate
    if not session:
        raise WallaAuthError(f"no {SESSION_COOKIE} in cookie paste")
    if " " in session or "\n" in session:
        raise WallaAuthError(
            "cookie value looks like pasted instructions, not the Value. "
            "Copy only the eyJ... string, or: walla login --cookies cookies.txt"
        )
    if session.startswith("eyJ") and (session.count(".") < 2 or len(session) < 200):
        raise WallaAuthError(
            "cookie value looks truncated. Prefer: walla login --cookies cookies.txt"
        )
    return session, device


def _strip_quotes(value: str) -> str:
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    return v


def _split_pair(pair: str) -> tuple[str, str]:
    if "=" in pair:
        name, _, value = pair.partition("=")
    else:
        name, _, value = pair.partition(":")
    return name.strip(), _strip_quotes(value.strip())


def _extract_named(line: str, cookie_name: str) -> str | None:
    for sep in (":", "="):
        prefix = f"{cookie_name}{sep}"
        if line.startswith(prefix):
            return _strip_quotes(line[len(prefix) :].strip())
        # also tolerate leading junk
        idx = line.find(prefix)
        if idx >= 0:
            return _strip_quotes(line[idx + len(prefix) :].strip())
    return None
