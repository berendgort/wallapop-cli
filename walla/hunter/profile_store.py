"""Profile store on disk."""

from __future__ import annotations

import json
from pathlib import Path

from walla.core.path import profile_path
from walla.models.profile import Profile

__all__ = (
    "load_profile",
    "parse_intake",
    "save_profile",
)


def load_profile(path: Path | None = None) -> Profile:
    p = path or profile_path()
    if not p.is_file():
        return Profile()
    data = json.loads(p.read_text(encoding="utf-8"))
    return Profile.model_validate(data)


def save_profile(profile: Profile, path: Path | None = None) -> Path:
    p = path or profile_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
    return p


def parse_intake(text: str) -> Profile:
    """Parse ``key=value`` intake line into a Profile."""
    fields: dict[str, str] = {}
    for part in text.replace(",", " ").split():
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        fields[k.strip().lower()] = v.strip()
    profile = load_profile()
    if "lat" in fields:
        profile.lat = float(fields["lat"])
    if "lon" in fields:
        profile.lon = float(fields["lon"])
    if "km" in fields:
        profile.km = float(fields["km"])
    if "pickup_km" in fields:
        profile.pickup_km = float(fields["pickup_km"])
    if "label" in fields:
        profile.label = fields["label"]
    if "budget" in fields:
        profile.budget = float(fields["budget"])
    if "max_price" in fields:
        profile.max_price = float(fields["max_price"])
    return profile
