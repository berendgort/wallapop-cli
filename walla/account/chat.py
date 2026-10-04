"""Open chat (Chat button) and send via PubNub."""

from __future__ import annotations

import json
import uuid
from typing import Any
from urllib.parse import quote

from curl_cffi import requests

from walla.account.login import ensure_access_token
from walla.core.exceptions import WallaUnsupportedError
from walla.http.client import HttpClient
from walla.http.headers import WEB_BASE, default_headers

__all__ = (
    "open_conversation",
    "publish_text",
    "resolve_conversation",
)

_PN_PUB = "pub-c-255dc549-86f5-4abd-8b9e-921d5a02fde7"
_PN_SUB = "sub-c-89405e27-d4df-4d87-aca1-d6e9118f0a0d"
_PN_ORIGIN = "https://ps2.pndsn.com"


def _auth_client() -> HttpClient:
    sess = ensure_access_token()
    return HttpClient(access_token=sess.access_token, device_id=sess.device_id)


def open_conversation(
    item_id: str, *, client: HttpClient | None = None
) -> dict[str, Any]:
    """Same as the listing Chat button: create or reuse a conversation."""
    http = client or _auth_client()
    raw = http.post(
        "/api/v3/conversations",
        json_body={"item_id": item_id},
        auth=True,
    )
    if not isinstance(raw, dict) or not raw.get("conversation_id"):
        raise WallaUnsupportedError(
            f"Chat open failed for {item_id}. Capture POST /api/v3/conversations."
        )
    return {
        "conversation_id": str(raw["conversation_id"]),
        "item_id": str(raw.get("item_id") or item_id),
        "other_user_id": str(raw["other_user_id"]) if raw.get("other_user_id") else None,
        "channel": str(raw["channel"]) if raw.get("channel") else None,
        "chat_url": f"{WEB_BASE}/app/chat?itemId={item_id}",
    }


def resolve_conversation(
    ref: str, *, client: HttpClient | None = None
) -> dict[str, Any]:
    """Resolve item id or conversation hash to an open conversation + channel."""
    http = client or _auth_client()
    from walla.account.inbox import list_conversations_raw

    inbox = list_conversations_raw(client=http)
    for row in inbox.get("conversations") or []:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("hash") or "")
        item = row.get("item") or {}
        item_hash = str(item.get("hash") or "") if isinstance(item, dict) else ""
        if ref in (cid, item_hash):
            with_user = row.get("with_user") or {}
            return {
                "conversation_id": cid,
                "item_id": item_hash or None,
                "other_user_id": (
                    str(with_user.get("hash"))
                    if isinstance(with_user, dict) and with_user.get("hash")
                    else None
                ),
                "channel": str(row["channel"]) if row.get("channel") else None,
                "user_hash": str(inbox.get("user_hash") or ""),
                "chat_url": (
                    f"{WEB_BASE}/app/chat?itemId={item_hash}" if item_hash else None
                ),
            }
    opened = open_conversation(ref, client=http)
    opened["user_hash"] = str(inbox.get("user_hash") or "")
    return opened


def publish_text(
    *,
    channel: str,
    conversation_id: str,
    from_user_hash: str,
    to_user_hash: str,
    text: str,
    client: HttpClient | None = None,
) -> dict[str, Any]:
    """Publish a chat text via Wallapop PubNub (REST message POST is 404)."""
    http = client or _auth_client()
    token_raw = http.get("/api/v3/instant-messaging/token", auth=True)
    if not isinstance(token_raw, dict) or not token_raw.get("token"):
        raise WallaUnsupportedError("Missing instant-messaging token.")
    pn_token = str(token_raw["token"])
    msg_id = str(uuid.uuid4())
    payload = json.dumps({"id": msg_id, "payload": {"text": text}})
    meta = json.dumps(
        {
            "type": "text",
            "sender": {"platform": {"app_version": "8.2616.0", "os_version": "0"}},
            "to_user_hash": to_user_hash,
            "from_user_hash": from_user_hash,
            "conversation_hash": conversation_id,
        }
    )
    url = (
        f"{_PN_ORIGIN}/publish/{_PN_PUB}/{_PN_SUB}/0/{quote(channel, safe='')}/0/"
        f"{quote(payload, safe='')}"
        f"?meta={quote(meta, safe='')}"
        f"&uuid={quote(from_user_hash, safe='')}"
        f"&requestid={uuid.uuid4()}"
        f"&pnsdk={quote('PubNub-JS-Web/10.2.6', safe='')}"
        f"&auth={quote(pn_token, safe='')}"
    )
    headers = default_headers(device_id=getattr(http, "device_id", None))
    headers["Accept"] = "*/*"
    headers["Origin"] = WEB_BASE
    headers["Referer"] = f"{WEB_BASE}/app/chat"
    resp = requests.get(url, headers=headers, impersonate="chrome", timeout=30)
    body = (resp.text or "").strip()
    if resp.status_code != 200 or not body.startswith("[1,"):
        raise WallaUnsupportedError(
            f"PubNub publish failed ({resp.status_code}): {body[:200]}"
        )
    return {"sent": True, "message_id": msg_id, "conversation_id": conversation_id}
