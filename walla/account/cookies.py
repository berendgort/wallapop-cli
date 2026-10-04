"""Parse browser cookie exports for NextAuth session."""

from __future__ import annotations

import json
from pathlib import Path

from walla.core.exceptions import WallaAuthError

__all__ = (
    "SESSION_COOKIE",
    "parse_cookie_export",
)

SESSION_COOKIE = "__Secure-next-auth.session-token"


def parse_cookie_export(path: Path) -> tuple[str, str | None]:
    """Return (session_cookie, device_id)."""
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
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
                    session = value
                elif name == "device_id":
                    device = value
            continue
        line = line.removeprefix("Cookie:").strip()
        for pair in line.split(";"):
            pair = pair.strip()
            if "=" not in pair:
                if pair.count(".") >= 2 and len(pair) > 100:
                    session = pair
                continue
            name, _, value = pair.partition("=")
            name, value = name.strip(), value.strip()
            if name == SESSION_COOKIE:
                session = value
            elif name == "device_id":
                device = value
    if not session and text.count(".") >= 2 and len(text) > 100 and "\n" not in text:
        session = text
    if not session:
        raise WallaAuthError(f"no {SESSION_COOKIE} in cookie export")
    return session, device
