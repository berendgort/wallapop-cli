"""Ask Wallapop to prefill category from title+photos (steps draft)."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from walla.account.sell_steps import (
    auth_client,
    parse_steps_draft,
    poll_suggested,
    post_step,
)
from walla.account.sell_upload import upload_pictures
from walla.search.api import get_categories
from walla.search.category_find import flatten_categories, resolve_root_id

__all__ = ("suggest_from_photos",)


def suggest_from_photos(
    photos: list[Path],
    *,
    title: str,
    root_category_id: str | None = None,
) -> dict[str, Any]:
    """Run title→photos→photo; return draft fields Wallapop injected."""
    paths = [Path(p) for p in photos]
    for p in paths:
        if not p.is_file():
            raise ValueError(f"photo not found: {p}")
    text = title.strip()[:50]
    if not text:
        raise ValueError("title required for suggest")
    http = auth_client()
    upload_id = str(uuid.uuid4())
    draft: dict[str, Any] = {"title": text}
    post_step(http, upload_id, current=None, draft={})
    post_step(http, upload_id, current="title", draft=draft)
    upload_pictures(upload_id, paths)
    after_photo = post_step(http, upload_id, current="photo", draft=draft)
    parsed = parse_steps_draft(after_photo)
    leaf = parsed.get("category_leaf_id")
    root = parsed.get("root_category_id") or root_category_id
    path = None
    if leaf:
        roots = get_categories()
        if not root:
            root = resolve_root_id(roots, leaf)
        path = next(
            (h.path for h in flatten_categories(roots) if h.leaf_id == leaf),
            None,
        )
        draft = {
            **draft,
            "category_leaf_id": leaf,
            "root_category_id": str(root),
        }
        post_step(http, upload_id, current="category", draft=draft)
        suggested_body = poll_suggested(http, upload_id)
        after_load = post_step(http, upload_id, current="loading", draft=draft)
        parsed = {**parsed, **parse_steps_draft(after_load)}
    else:
        suggested_body = None
    return {
        "upload_id": upload_id,
        "title": parsed.get("title") or text,
        "category_leaf_id": leaf,
        "root_category_id": str(root) if root else None,
        "path": path,
        "suggested_item_data": suggested_body,
        "hint": (
            "Wallapop filled category_leaf_id from title+photos when present. "
            "Pass --category / --title overrides, then --yes to publish."
        ),
    }
