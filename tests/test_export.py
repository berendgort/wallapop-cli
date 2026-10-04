"""Shortlist export unit tests."""

from __future__ import annotations

from pathlib import Path

from walla.hunter.export import fit_line, write_exports
from walla.models.profile import Profile


def _row() -> dict:
    return {
        "id": "abc",
        "title": "Tabla kite Cabrinha 10m",
        "description": "cabrinha kite",
        "price": {"amount": 320.0, "currency": "EUR"},
        "web_slug": "tabla-kite",
        "url": "https://es.wallapop.com/item/tabla-kite-cabrinha",
        "verdict": "GRAB",
        "location": {"latitude": 41.39, "longitude": 2.17},
        "user_allows_shipping": False,
        "shippable": False,
    }


def test_write_all_formats(tmp_path: Path) -> None:
    profile = Profile(
        lat=41.39, lon=2.17, km=30, budget=400, must_match=["kite"]
    )
    written = write_exports(
        [_row()],
        profile,
        formats=["md", "csv", "html", "pdf"],
        out_dir=tmp_path,
        keywords="tabla kite",
    )
    assert set(written) == {"md", "csv", "html", "pdf"}
    md = (tmp_path / "walla-shortlist.md").read_text(encoding="utf-8")
    assert "https://es.wallapop.com/item/" in md
    assert "400" in md or "budget" in md.lower() or "under" in md
    csv = (tmp_path / "walla-shortlist.csv").read_text(encoding="utf-8")
    assert "title,price_eur,verdict,url,fit" in csv
    html = (tmp_path / "walla-shortlist.html").read_text(encoding="utf-8")
    assert "<a href='https://es.wallapop.com/item/" in html
    pdf = (tmp_path / "walla-shortlist.pdf").read_bytes()
    assert pdf.startswith(b"%PDF")
    assert b"es.wallapop.com" in pdf


def test_fit_mentions_budget() -> None:
    profile = Profile(lat=41.39, lon=2.17, km=30, budget=400, must_match=["kite"])
    fit = fit_line(_row(), profile)
    assert "400" in fit
    assert "GRAB" in fit
    assert "kite" in fit.lower()
