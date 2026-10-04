"""Config paths under ``~/.config/walla`` (override ``WALLA_CONFIG_DIR``)."""

from __future__ import annotations

import os
from pathlib import Path

__all__ = (
    "config_dir",
    "last_search_path",
    "profile_path",
    "session_path",
    "watches_path",
)


def config_dir() -> Path:
    override = os.environ.get("WALLA_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "walla"


def profile_path() -> Path:
    return config_dir() / "profile.json"


def session_path() -> Path:
    return config_dir() / "session.json"


def watches_path() -> Path:
    return config_dir() / "watches.json"


def last_search_path() -> Path:
    return config_dir() / "last_search.json"
