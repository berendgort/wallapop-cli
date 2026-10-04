"""Authenticated inbox / thread / send."""

from __future__ import annotations

from typing import Any, cast

from walla.account.login import ensure_access_token
from walla.core.exceptions import WallaUnsupportedError
from walla.http.client import HttpClient
from walla.models.account import Conversation, Message

__all__ = (
    "list_conversations",
    "list_messages",
    "send_message",
)


def _auth_client() -> HttpClient:
    sess = ensure_access_token()
    return HttpClient(access_token=sess.access_token, device_id=sess.device_id)


def list_conversations(*, client: HttpClient | None = None) -> list[Conversation]:
    http = client or _auth_client()
    raw = http.get("/api/v3/conversations", params={"max_messages": 1}, auth=True)
    rows = _extract_list(raw)
    out: list[Conversation] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("id") or row.get("conversation_id") or "")
        if not cid:
            continue
        item = row.get("item") or row.get("product") or {}
        user = row.get("user") or row.get("other_user") or {}
        last = row.get("last_message") or row.get("messages") or {}
        last_text = None
        if isinstance(last, dict):
            last_text = last.get("text") or last.get("message")
        elif isinstance(last, list) and last:
            last_text = last[0].get("text") if isinstance(last[0], dict) else None
        out.append(
            Conversation(
                id=cid,
                item_id=str(item.get("id")) if isinstance(item, dict) and item.get("id") else None,
                item_title=item.get("title") if isinstance(item, dict) else None,
                other_user=(
                    user.get("micro_name") or user.get("name")
                    if isinstance(user, dict)
                    else None
                ),
                unread=int(row.get("unread_count") or row.get("unread") or 0),
                last_message=str(last_text) if last_text else None,
            )
        )
    return out


def list_messages(conversation_id: str, *, client: HttpClient | None = None) -> list[Message]:
    http = client or _auth_client()
    # Try common shapes; first success wins.
    for path in (
        f"/api/v3/conversations/{conversation_id}/messages",
        f"/api/v3/conversations/{conversation_id}",
    ):
        try:
            raw = http.get(path, auth=True)
        except Exception:  # noqa: BLE001
            continue
        rows = _extract_messages(raw)
        if rows is not None:
            return rows
    raise WallaUnsupportedError(
        "Message thread wire not confirmed for this account. "
        "Capture GET conversation messages and update docs/WIRE.md."
    )


def send_message(
    conversation_id: str,
    text: str,
    *,
    confirm: bool = False,
    client: HttpClient | None = None,
) -> dict[str, Any]:
    if not confirm:
        raise ValueError("send requires confirm=True / --yes")
    http = client or _auth_client()
    try:
        raw = http.post(
            f"/api/v3/conversations/{conversation_id}/messages",
            json_body={"text": text, "message": text},
            auth=True,
        )
        return {"sent": True, "conversation_id": conversation_id, "response": raw}
    except Exception as exc:
        raise WallaUnsupportedError(
            f"Send wire failed ({exc}). Capture POST messages and update docs/WIRE.md."
        ) from exc


def _extract_list(raw: Any) -> list[Any]:
    if isinstance(raw, list):
        return raw
    if not isinstance(raw, dict):
        return []
    for key in ("conversations", "data", "items"):
        val = raw.get(key)
        if isinstance(val, list):
            return val
        if isinstance(val, dict):
            for k2 in ("conversations", "items", "list"):
                if isinstance(val.get(k2), list):
                    return cast(list[Any], val[k2])
    return []


def _extract_messages(raw: Any) -> list[Message] | None:
    rows: list[Any] | None = None
    if isinstance(raw, list):
        rows = raw
    elif isinstance(raw, dict):
        for key in ("messages", "data", "items"):
            val = raw.get(key)
            if isinstance(val, list):
                rows = val
                break
            if isinstance(val, dict) and isinstance(val.get("messages"), list):
                rows = val["messages"]
                break
    if rows is None:
        return None
    out: list[Message] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        text = row.get("text") or row.get("message") or ""
        out.append(
            Message(
                id=str(row["id"]) if row.get("id") else None,
                text=str(text),
                from_self=bool(row.get("from_self") or row.get("mine")),
                created_at=row.get("created_at") or row.get("timestamp"),
            )
        )
    return out
