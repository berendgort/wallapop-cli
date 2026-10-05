"""Ranked shortlist for agents (pure; no HTTP)."""

from __future__ import annotations

from typing import Any

__all__ = ("PRESENT_RULE", "rank_shortlist", "soft_shortlist")

_VERDICT_RANK = {"GRAB": 0, "LOOK": 1, "PASS": 2}

PRESENT_RULE = (
    "Always say these are Wallapop.es listings. Present a numbered shortlist "
    "ranked best-first (GRAB before LOOK; lower EUR first). Each row must "
    "include the full https://es.wallapop.com/item/… URL as a markdown link. "
    "Never summarize without links."
)


def rank_shortlist(
    listings: list[dict[str, Any]],
    *,
    limit: int = 12,
    include_pass: bool = False,
) -> list[dict[str, Any]]:
    """Return ranked rows: GRAB then LOOK then PASS; cheaper first within band."""
    scored: list[tuple[int, float, dict[str, Any]]] = []
    for row in listings:
        verdict = str(row.get("verdict") or "LOOK")
        if verdict == "PASS" and not include_pass:
            continue
        price = row.get("price") or {}
        amount = float(price.get("amount") or 0) if isinstance(price, dict) else 0.0
        scored.append((_VERDICT_RANK.get(verdict, 9), amount, row))
    scored.sort(key=lambda t: (t[0], t[1]))
    out: list[dict[str, Any]] = []
    for i, (_, amount, row) in enumerate(scored[:limit], start=1):
        loc = row.get("location") or {}
        city = loc.get("city") if isinstance(loc, dict) else None
        out.append(
            {
                "rank": i,
                "id": row.get("id"),
                "title": row.get("title"),
                "price_eur": amount,
                "verdict": row.get("verdict"),
                "url": row.get("url"),
                "city": city,
                "shippable": bool(
                    row.get("user_allows_shipping") or row.get("shippable")
                ),
            }
        )
    return out


def soft_shortlist(
    listings: list[dict[str, Any]],
    *,
    must_match: list[str],
    limit: int = 12,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Rank GRAB/LOOK; if empty and mandate set, fall back treating PASS as LOOK."""
    hard = rank_shortlist(listings, limit=limit)
    if hard or not must_match or not listings:
        return hard, None
    soft_rows: list[dict[str, Any]] = []
    for row in listings:
        copy = dict(row)
        if copy.get("verdict") == "PASS":
            copy["verdict"] = "LOOK"
        soft_rows.append(copy)
    soft = rank_shortlist(soft_rows, limit=limit)
    note = {
        "mandate_emptied": True,
        "must_match": list(must_match),
        "how": "walla setup --must ''   # clear sticky mandate for a new hunt",
        "note": (
            "Shortlist fell back because must_match PASSed every hit. "
            "Clear the mandate or include those words in the query."
        ),
    }
    return soft, note
