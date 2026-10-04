"""Load ``WALLAPOP_USER`` / ``WALLAPOP_PW`` without echoing secrets."""

from __future__ import annotations

import os
from pathlib import Path

from walla.core.path import config_dir

__all__ = (
    "credentials_configured",
    "load_credentials",
    "load_dotenv_files",
)


def load_dotenv_files() -> None:
    """Load cwd ``.env`` then ``~/.config/walla/.env`` into os.environ (no overwrite)."""
    for path in (Path.cwd() / ".env", config_dir() / ".env"):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value


def load_credentials() -> tuple[str | None, str | None]:
    load_dotenv_files()
    user = os.environ.get("WALLAPOP_USER") or os.environ.get("WALLAPOP_EMAIL")
    pw = os.environ.get("WALLAPOP_PW") or os.environ.get("WALLAPOP_PASSWORD")
    return (user or None, pw or None)


def credentials_configured() -> bool:
    user, pw = load_credentials()
    return bool(user and pw)
