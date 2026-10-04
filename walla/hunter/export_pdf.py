"""Minimal PDF writer for shortlists (no third-party deps)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ("write_shortlist_pdf",)


def write_shortlist_pdf(
    rows: list[dict[str, Any]], keywords: str, path: Path
) -> None:
    lines = ["walla shortlist"]
    if keywords:
        lines.append(f"Query: {keywords}")
    lines.append("")
    for r in rows:
        price = r.get("price_eur", 0)
        price_s = str(int(price)) if float(price).is_integer() else f"{float(price):.2f}"
        lines.append(str(r.get("title") or "")[:70])
        lines.append(
            f"  {price_s} EUR | {r.get('verdict')} | {str(r.get('fit') or '')[:60]}"
        )
        lines.append(f"  {r.get('url')}")
        lines.append("")
    content = _text_stream(lines)
    objects: list[bytes] = [
        b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n",
        b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n",
        (
            b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
        ),
        (
            f"4 0 obj<< /Length {len(content)} >>stream\n".encode()
            + content
            + b"\nendstream\nendobj\n"
        ),
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(
        f"trailer<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode()
    )
    path.write_bytes(bytes(out))


def _text_stream(lines: list[str]) -> bytes:
    cmds = ["BT", "/F1 10 Tf", "14 TL", "50 760 Td"]
    first = True
    for raw in lines[:55]:
        safe = (
            raw.replace("\\", "\\\\")
            .replace("(", "\\(")
            .replace(")", "\\)")
            .encode("latin-1", errors="replace")
            .decode("latin-1")
        )
        if not first:
            cmds.append("T*")
        first = False
        cmds.append(f"({safe}) Tj")
    cmds.append("ET")
    return "\n".join(cmds).encode("latin-1")
