"""Shared Vender step helpers (auth + /api/v3/steps + suggest poll)."""

from __future__ import annotations

from typing import Any

from walla.account.login import ensure_access_token
from walla.core.exceptions import WallaHTTPError, WallaUnsupportedError
from walla.http.client import HttpClient
from walla.http.headers import default_headers
from walla.http.polite import wait_turn

__all__ = (
    "auth_client",
    "auth_headers",
    "parse_steps_draft",
    "poll_suggested",
    "post_step",
)


def auth_client() -> HttpClient:
    sess = ensure_access_token()
    return HttpClient(access_token=sess.access_token, device_id=sess.device_id)


def auth_headers() -> dict[str, str]:
    sess = ensure_access_token()
    headers = default_headers(device_id=sess.device_id)
    headers["Authorization"] = f"Bearer {sess.access_token}"
    return headers


def post_step(
    http: HttpClient,
    upload_id: str,
    *,
    current: str | None,
    draft: dict[str, Any],
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "mode": {"action": "upload", "id": upload_id},
        "draft": draft,
    }
    if current:
        body["current_step"] = current
    raw = http.post("/api/v3/steps", json_body=body, auth=True)
    if not isinstance(raw, dict):
        raise WallaUnsupportedError("steps returned non-object")
    return raw


def poll_suggested(http: HttpClient, upload_id: str, *, attempts: int = 8) -> Any:
    """GET suggested-item-data until non-404 (body often empty 200)."""
    last: Any = None
    for _ in range(attempts):
        wait_turn()
        try:
            last = http.get(f"/api/v3/suggested-item-data/{upload_id}", auth=True)
            return last
        except WallaHTTPError as exc:
            if exc.status_code != 404:
                raise
    return last


def parse_steps_draft(payload: dict[str, Any]) -> dict[str, str]:
    """Pull title/category ids from a steps response draft."""
    draft = payload.get("draft")
    if not isinstance(draft, dict):
        return {}
    out: dict[str, str] = {}
    title = draft.get("title")
    if title:
        out["title"] = str(title).strip()[:50]
    leaf = draft.get("category_leaf_id") or draft.get("categoryLeafId")
    if leaf:
        out["category_leaf_id"] = str(leaf)
    root = draft.get("root_category_id") or draft.get("rootCategoryId")
    if root:
        out["root_category_id"] = str(root)
    return out
