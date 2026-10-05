"""Resolve sell category leaf/root from an id or name query."""

from __future__ import annotations

from walla.models.profile import Category
from walla.search.category_find import CategoryHit, find_categories, flatten_categories

__all__ = ("pick_sell_category",)


def pick_sell_category(
    roots: list[Category],
    *,
    category: str,
    root: str | None = None,
) -> CategoryHit:
    """Accept a leaf id or a find query; derive root when omitted."""
    text = category.strip()
    if not text:
        raise ValueError("category is empty")
    forced = str(root).strip() if root else None
    if text.isdigit():
        hit = next((h for h in flatten_categories(roots) if h.leaf_id == text), None)
        if hit is None:
            raise ValueError(f"unknown category leaf id: {text}")
        return CategoryHit(
            leaf_id=hit.leaf_id,
            root_id=forced or hit.root_id,
            path=hit.path,
            name=hit.name,
            is_leaf=hit.is_leaf,
        )
    hits = find_categories(roots, text)
    if not hits:
        raise ValueError(
            f"no category matches {text!r}; try: walla categories --find {text!r}"
        )
    best = hits[0]
    if forced:
        return CategoryHit(
            leaf_id=best.leaf_id,
            root_id=forced,
            path=best.path,
            name=best.name,
            is_leaf=best.is_leaf,
        )
    _reject_ambiguous_name(text, hits)
    return best


def _reject_ambiguous_name(query: str, hits: list[CategoryHit]) -> None:
    """Fail closed when one bare leaf name maps to several roots."""
    tokens = [t for t in query.lower().replace("/", " ").split() if t]
    if len(tokens) != 1:
        return
    needle = tokens[0]
    exact = [
        h
        for h in hits
        if h.is_leaf and h.name.lower() == needle
    ]
    roots = {h.root_id for h in exact}
    if len(roots) <= 1:
        return
    sample = "; ".join(f"{h.path} leaf={h.leaf_id}" for h in exact[:6])
    raise ValueError(
        f"ambiguous category {query!r} spans roots; pass leaf id or "
        f"disambiguate (e.g. 'motor accesorios'): {sample}"
    )
