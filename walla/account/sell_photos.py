"""Normalize sell photo paths (HEIC -> JPEG via ImageMagick when needed)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from walla.account.sell_upload import IMAGE_TYPES

__all__ = ("prepare_sell_photos",)

_HEIC = {".heic", ".heif"}


def prepare_sell_photos(photos: list[Path]) -> list[Path]:
    """Return paths Wallapop accepts; convert HEIC/HEIF when convert/magick exists."""
    if not photos:
        raise ValueError("at least one photo required")
    out: list[Path] = []
    for path in photos:
        p = path.expanduser()
        if not p.is_file():
            raise ValueError(f"photo not found: {p}")
        suf = p.suffix.lower()
        if suf in IMAGE_TYPES:
            out.append(p)
            continue
        if suf in _HEIC:
            out.append(_heic_to_jpeg(p))
            continue
        raise ValueError(
            f"unsupported photo type {suf} ({p.name}); use JPEG/PNG/WebP/HEIC"
        )
    return out


def _heic_to_jpeg(src: Path) -> Path:
    dest = src.with_suffix(".jpg")
    if dest.is_file() and dest.stat().st_mtime >= src.stat().st_mtime:
        return dest
    tool = shutil.which("magick") or shutil.which("convert")
    if not tool:
        raise ValueError(
            f"HEIC needs ImageMagick (magick/convert) to encode JPEG: {src.name}"
        )
    cmd = (
        [tool, str(src), str(dest)]
        if Path(tool).name == "convert"
        else [tool, str(src), str(dest)]
    )
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not dest.is_file():
        err = (proc.stderr or proc.stdout or "").strip()[:200]
        raise ValueError(f"HEIC convert failed for {src.name}: {err or 'unknown'}")
    return dest
