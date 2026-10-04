"""Authenticated inbox / thread / send."""

from __future__ import annotations

from typing import Any, cast

from walla.account.login import ensure_access_token
from walla.core.exceptions import WallaUnsupportedError
from walla.http.client import HttpClient
from walla.models.account import Conversation, Message

__all__ = (
    "list_conversations",
    "list_conversations_raw",
    "list_messages",
    "send_message",
)


def _auth_client() -> HttpClient:
    sess = ensure_access_token()
    return HttpClient(access_token=sess.access_token, device_id=sess.device_id)


def list_conversations_raw(*, client: HttpClient | None = None) -> dict[str, Any]:
    http = client or _auth_client()
    raw = http.get(
        "/bff/messaging/inbox",
        params={"page_size": 30, "max_messages": 30},
        auth=True,
    )
    if not isinstance(raw, dict):
        raise WallaUnsupportedError("Inbox BFF returned non-object.")
    return raw


def list_conversations(*, client: HttpClient | None = None) -> list[Conversation]:
    raw = list_conversations_raw(client=client)
    out: list[Conversation] = []
    for row in raw.get("conversations") or []:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("hash") or row.get("id") or "")
        if not cid:
            continue
        item = row.get("item") or {}
        user = row.get("with_user") or row.get("user") or {}
        msgs = row.get("messages") or {}
        last_text = None
        if isinstance(msgs, dict):
            inner = msgs.get("messages") or []
            if isinstance(inner, list) and inner and isinstance(inner[0], dict):
                last_text = inner[0].get("text")
        out.append(
            Conversation(
                id=cid,
                item_id=(
                    str(item.get("hash") or item.get("id"))
                    if isinstance(item, dict)
                    and (item.get("hash") or item.get("id"))
                    else None
                ),
                item_title=item.get("title") if isinstance(item, dict) else None,
                other_user=(
                    user.get("name") or user.get("micro_name")
                    if isinstance(user, dict)
                    else None
                ),
                unread=int(row.get("unread_messages") or row.get("unread") or 0),
                last_message=str(last_text) if last_text else None,
            )
        )
    return out


def list_messages(conversation_id: str, *, client: HttpClient | None = None) -> list[Message]:
    raw = list_conversations_raw(client=client)
    for row in raw.get("conversations") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("hash") or "") != conversation_id:
            continue
        msgs = row.get("messages") or {}
        inner: list[Any] = []
        if isinstance(msgs, dict):
            inner = cast(list[Any], msgs.get("messages") or [])
        elif isinstance(msgs, list):
            inner = msgs
        out: list[Message] = []
        for m in inner:
            if not isinstance(m, dict):
                continue
            out.append(
                Message(
                    id=str(m["id"]) if m.get("id") else None,
                    text=str(m.get("text") or ""),
                    from_self=bool(m.get("from_self")),
                    created_at=m.get("timestamp") or m.get("created_at"),
                )
            )
        return out
    raise WallaUnsupportedError(
        f"Conversation {conversation_id} not in inbox. "
        "Open chat first: walla chat <item_id> --json"
    )


def send_message(
    target: str,
    text: str,
    *,
    confirm: bool = False,
    client: HttpClient | None = None,
) -> dict[str, Any]:
    """Send chat text. ``target`` is an item id or conversation hash."""
    if not confirm:
        raise ValueError("send requires confirm=True / --yes")
    from walla.account.chat import publish_text, resolve_conversation

    http = client or _auth_client()
    opened = resolve_conversation(target, client=http)
    channel = opened.get("channel")
    from_user = opened.get("user_hash") or ""
    to_user = opened.get("other_user_id") or ""
    cid = str(opened["conversation_id"])
    if not channel or not from_user or not to_user:
        # reopen create endpoint for channel + other_user
        from walla.account.chat import open_conversation

        item_id = opened.get("item_id") or target
        opened = open_conversation(str(item_id), client=http)
        channel = opened.get("channel")
        to_user = opened.get("other_user_id") or ""
        cid = str(opened["conversation_id"])
        raw = list_conversations_raw(client=http)
        from_user = str(raw.get("user_hash") or "")
    if not channel or not from_user or not to_user:
        raise WallaUnsupportedError(
            "Chat missing channel/users after open. Capture conversation create."
        )
    sent = publish_text(
        channel=str(channel),
        conversation_id=cid,
        from_user_hash=from_user,
        to_user_hash=str(to_user),
        text=text,
        client=http,
    )
    sent["item_id"] = opened.get("item_id")
    sent["chat_url"] = opened.get("chat_url")
    return sent
