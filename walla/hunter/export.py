"""Shortlist export: md, csv, html, pdf (no secrets)."""

from __future__ import annotations

import csv
import html
import json
from io import StringIO
from pathlib import Path
from typing import Any

from walla.core.path import last_search_path as _last_search_path
from walla.hunter.export_pdf import write_shortlist_pdf
from walla.hunter.verdict import haversine_km, matches_must
from walla.models.listing import Listing, ListingLocation, Money
from walla.models.profile import Profile

__all__ = (
    "EXPORT_FORMATS",
    "fit_line",
    "last_search_path",
    "load_last_search",
    "save_last_search",
    "write_exports",
)

EXPORT_FORMATS = ("md", "csv", "html", "pdf")


def last_search_path() -> Path:
    return _last_search_path()


def save_last_search(
    *,
    keywords: str,
    listings: list[dict[str, Any]],
    mandate: dict[str, Any],
) -> Path:
    path = last_search_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"keywords": keywords, "listings": listings, "mandate": mandate},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def load_last_search() -> dict[str, Any]:
    path = last_search_path()
    if not path.is_file():
        raise ValueError(
            "No last search. Run walla search … first, then walla export."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("last_search.json is not an object")
    return data


def fit_line(row: dict[str, Any], profile: Profile) -> str:
    listing = _row_to_listing(row)
    verdict = str(row.get("verdict") or "?")
    price = float(listing.price.amount)
    parts = [verdict, f"{_fmt(price)} EUR"]
    cap = profile.spend_cap
    if cap is not None:
        if price <= cap:
            parts.append(f"under {_fmt(cap)} budget")
        else:
            parts.append(f"over {_fmt(cap)} budget")
    if profile.must_match:
        if matches_must(listing, profile):
            parts.append("matches " + " ".join(profile.must_match))
        else:
            parts.append("missing must_match")
    if (
        profile.lat is not None
        and profile.lon is not None
        and listing.location
        and listing.location.latitude is not None
        and listing.location.longitude is not None
    ):
        dist = haversine_km(
            profile.lat,
            profile.lon,
            listing.location.latitude,
            listing.location.longitude,
        )
        if dist <= profile.km:
            parts.append(f"inside {_fmt(profile.km)} km")
        else:
            parts.append(f"{dist:.0f} km away")
    return " · ".join(parts)


def write_exports(
    listings: list[dict[str, Any]],
    profile: Profile,
    *,
    formats: list[str],
    out_dir: Path,
    keywords: str = "",
) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [_enriched(r, profile) for r in listings]
    written: dict[str, str] = {}
    wanted = {f.strip().lower() for f in formats if f.strip()}
    unknown = wanted - set(EXPORT_FORMATS)
    if unknown:
        raise ValueError(f"unknown export format(s): {sorted(unknown)}")
    if "md" in wanted:
        path = out_dir / "walla-shortlist.md"
        path.write_text(_to_md(rows, keywords), encoding="utf-8")
        written["md"] = str(path)
    if "csv" in wanted:
        path = out_dir / "walla-shortlist.csv"
        path.write_text(_to_csv(rows), encoding="utf-8")
        written["csv"] = str(path)
    if "html" in wanted:
        path = out_dir / "walla-shortlist.html"
        path.write_text(_to_html(rows, keywords), encoding="utf-8")
        written["html"] = str(path)
    if "pdf" in wanted:
        path = out_dir / "walla-shortlist.pdf"
        write_shortlist_pdf(rows, keywords, path)
        written["pdf"] = str(path)
    return written


def _enriched(row: dict[str, Any], profile: Profile) -> dict[str, Any]:
    price = row.get("price") or {}
    amount = price.get("amount") if isinstance(price, dict) else None
    return {
        "title": str(row.get("title") or ""),
        "price_eur": float(amount) if amount is not None else 0.0,
        "verdict": str(row.get("verdict") or ""),
        "url": str(row.get("url") or ""),
        "fit": fit_line(row, profile),
    }


def _row_to_listing(row: dict[str, Any]) -> Listing:
    price = row.get("price") or {}
    amount = float(price.get("amount") or 0) if isinstance(price, dict) else 0.0
    loc_raw = row.get("location") or {}
    loc = None
    if isinstance(loc_raw, dict):
        loc = ListingLocation(
            latitude=loc_raw.get("latitude"),
            longitude=loc_raw.get("longitude"),
            city=loc_raw.get("city"),
        )
    return Listing(
        id=str(row.get("id") or "x"),
        title=str(row.get("title") or ""),
        description=row.get("description"),
        price=Money(amount=amount),
        web_slug=str(row.get("web_slug") or "x"),
        url=str(row.get("url") or ""),
        location=loc,
        user_allows_shipping=bool(row.get("user_allows_shipping")),
        shippable=bool(row.get("shippable")),
    )


def _fmt(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else f"{n:.2f}"


def _to_md(rows: list[dict[str, Any]], keywords: str) -> str:
    lines = ["# walla shortlist", ""]
    if keywords:
        lines.append(f"Query: `{keywords}`")
        lines.append("")
    for r in rows:
        lines.append(f"## {r['title']}")
        lines.append("")
        lines.append(f"- Price: {_fmt(r['price_eur'])} EUR")
        lines.append(f"- Verdict: {r['verdict']}")
        lines.append(f"- Fit: {r['fit']}")
        lines.append(f"- Link: {r['url']}")
        lines.append("")
    return "\n".join(lines)


def _to_csv(rows: list[dict[str, Any]]) -> str:
    buf = StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=["title", "price_eur", "verdict", "url", "fit"]
    )
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    return buf.getvalue()


def _to_html(rows: list[dict[str, Any]], keywords: str) -> str:
    parts = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'>",
        "<title>walla shortlist</title>",
        "<style>body{font-family:system-ui,sans-serif;max-width:720px;margin:2rem auto}",
        "a{color:#0a7} table{border-collapse:collapse;width:100%}",
        "td,th{border:1px solid #ddd;padding:.4rem;text-align:left}</style>",
        "</head><body>",
        "<h1>walla shortlist</h1>",
    ]
    if keywords:
        parts.append(f"<p>Query: <code>{html.escape(keywords)}</code></p>")
    parts.append(
        "<table><tr><th>Title</th><th>EUR</th><th>Verdict</th><th>Fit</th></tr>"
    )
    for r in rows:
        parts.append(
            "<tr>"
            f"<td><a href='{html.escape(r['url'])}'>{html.escape(r['title'])}</a></td>"
            f"<td>{_fmt(r['price_eur'])}</td>"
            f"<td>{html.escape(r['verdict'])}</td>"
            f"<td>{html.escape(r['fit'])}</td>"
            "</tr>"
        )
    parts.append("</table></body></html>")
    return "\n".join(parts)
