"""Chat text that reads like someone typing on a phone, not a letter."""

from __future__ import annotations

import re

__all__ = ("human",)


def human(text: str) -> str:
    """One line, no ¡/¿, lowercase start, no closing period, 250€ not 250 €."""
    t = " ".join(text.split()).replace("¡", "").replace("¿", "")
    t = re.sub(r"(\d)\s+€", r"\1€", t)
    t = re.sub(r"!{2,}", "!", t)
    first = t.split(" ", 1)[0]
    if first[:1].isupper() and first[1:].islower():  # keeps "S23", "OK", "iPhone"
        t = t[0].lower() + t[1:]
    return t.rstrip(".")
