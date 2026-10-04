"""Session persistence (mode 0600). Never stores the password."""

from __future__ import annotations

import os
from pathlib import Path

from walla.core.path import session_path
from walla.models.account import SessionData

__all__ = (
    "clear_session",
    "load_session",
    "save_session",
)


def load_session(path: Path | None = None) -> SessionData | None:
    p = path or session_path()
    if not p.is_file():
        return None
    return SessionData.model_validate_json(p.read_text(encoding="utf-8"))


def save_session(session: SessionData, path: Path | None = None) -> Path:
    p = path or session_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(session.model_dump_json(indent=2), encoding="utf-8")
    os.chmod(p, 0o600)
    return p


def clear_session(path: Path | None = None) -> None:
    p = path or session_path()
    if p.is_file():
        p.unlink()
