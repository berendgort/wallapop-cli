"""Search a wave, send the opening, then advance inbox threads. One inbox read."""

from __future__ import annotations

from typing import Any

from walla.account.inbox import list_conversations_raw, send_message
from walla.http.client import HttpClient
from walla.hunter.converge import next_move
from walla.hunter.negotiate import draft_negotiation
from walla.hunter.profile_store import load_profile
from walla.hunter.pursuits import Pursuit, load_pursuits, remember, save_pursuits
from walla.hunter.stack import stack_summary
from walla.hunter.verdict import score_listing
from walla.models.account import Message
from walla.models.listing import Listing
from walla.search.api import search_listings

__all__ = (
    "run_desk",
    "run_pursue",
)

_WAVE_CAP = 15


def run_pursue(
    keywords: str,
    *,
    wave: int = 5,
    local: bool = False,
    client: HttpClient | None = None,
) -> dict[str, Any]:
    """Message the best listings, then read the inbox once and answer."""
    profile = load_profile()
    if not profile.ready:
        return {"ready": False, "intake": {"prompt_to_user": profile.intake_prompt()}}
    found = search_listings(
        keywords,
        latitude=float(profile.lat or 0),
        longitude=float(profile.lon or 0),
        max_results=40,
        max_price=profile.budget,
        client=client,
    )
    ranked: list[tuple[str, Listing]] = []
    for listing in found.listings:
        verdict = score_listing(listing, profile, local=local)
        if verdict in ("GRAB", "LOOK"):
            ranked.append((verdict, listing))
    ranked.sort(key=lambda row: (0 if row[0] == "GRAB" else 1, row[1].price.amount))
    known = {row.item_id for row in load_pursuits().pursuits}
    sent: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    limit = max(1, min(wave, _WAVE_CAP))
    for verdict, listing in ranked:
        if len(sent) >= limit:
            break
        if listing.id in known:
            skipped.append({"item_id": listing.id, "reason": "already in the stack"})
            continue
        try:
            brief = draft_negotiation(listing, profile)
        except ValueError as exc:
            skipped.append({"item_id": listing.id, "reason": str(exc)})
            continue
        text = f"{brief.opening}\n\n{brief.offer_line}"
        try:
            send_message(listing.id, text, confirm=True, client=client)
        except Exception as exc:  # noqa: BLE001
            skipped.append({"item_id": listing.id, "reason": str(exc)})
            continue
        remember(
            Pursuit(
                item_id=listing.id,
                title=listing.title,
                url=listing.url,
                side="buy",
                ask_eur=brief.ask_eur,
                offer_eur=brief.offer_eur,
                walk_away_eur=brief.walk_away_eur,
                query=keywords,
                status="waiting",
                why=brief.why,
            )
        )
        known.add(listing.id)
        sent.append(
            {
                "item_id": listing.id,
                "title": listing.title,
                "url": listing.url,
                "verdict": verdict,
                "offer_eur": brief.offer_eur,
                "text": text,
            }
        )
    followed = run_desk(client=client)
    return {
        "query": keywords,
        "sent": sent,
        "skipped": skipped,
        "stack": followed["stack"],
        "replies": followed["replies"],
        "close_in_app": True,
    }


def run_desk(*, client: HttpClient | None = None) -> dict[str, Any]:
    """One inbox read. Reply where the other person spoke. Summarize agreements."""
    raw = list_conversations_raw(client=client)
    threads = _threads(raw)
    store = load_pursuits()
    by_id = {row.item_id: row for row in store.pursuits}
    for item_id, _messages in threads.items():
        if item_id in by_id:
            continue
        adopted = _adopt_sale(raw, item_id)
        if adopted is not None:
            by_id[item_id] = adopted
    replies: list[dict[str, Any]] = []
    updated: list[Pursuit] = []
    for pursuit in by_id.values():
        messages = threads.get(pursuit.item_id, [])
        move = next_move(pursuit, messages)
        row = pursuit.model_copy(
            update={
                "nudges": move.nudges,
                "offer_eur": move.offer_eur if move.offer_eur is not None else pursuit.offer_eur,
                "why": move.why,
            }
        )
        if move.action == "send" and move.text:
            try:
                send_message(pursuit.item_id, move.text, confirm=True, client=client)
            except Exception as exc:  # noqa: BLE001
                replies.append({"item_id": pursuit.item_id, "action": "error", "why": str(exc)})
                updated.append(row)
                continue
            row = row.model_copy(update={"status": "waiting"})
        elif move.action == "converged":
            row = row.model_copy(
                update={"status": "converged", "agreed_eur": move.agreed_eur}
            )
        elif move.action == "walk":
            row = row.model_copy(update={"status": "walked"})
        elif move.action == "wait" and row.status == "open":
            row = row.model_copy(update={"status": "waiting"})
        replies.append(
            {
                "item_id": pursuit.item_id,
                "title": pursuit.title,
                "url": pursuit.url,
                "action": move.action,
                "why": move.why,
                "offer_eur": row.offer_eur,
                "agreed_eur": row.agreed_eur,
            }
        )
        updated.append(row)
    save_pursuits(store.model_copy(update={"pursuits": updated}))
    return {"replies": replies, "stack": stack_summary(updated), "close_in_app": True}


def _threads(raw: dict[str, Any]) -> dict[str, list[Message]]:
    out: dict[str, list[Message]] = {}
    for row in raw.get("conversations") or []:
        if not isinstance(row, dict):
            continue
        item = row.get("item") or {}
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("hash") or item.get("id") or "")
        if not item_id:
            continue
        msgs = row.get("messages") or {}
        inner = msgs.get("messages") if isinstance(msgs, dict) else msgs
        parsed: list[Message] = []
        if isinstance(inner, list):
            for blob in inner:
                if not isinstance(blob, dict):
                    continue
                if blob.get("type") not in (None, "text"):
                    continue
                parsed.append(
                    Message(
                        id=str(blob["id"]) if blob.get("id") else None,
                        text=str(blob.get("text") or ""),
                        from_self=bool(blob.get("from_self")),
                        created_at=blob.get("timestamp") or blob.get("created_at"),
                    )
                )
        if parsed and all(m.created_at is None for m in parsed):
            parsed.reverse()
        else:
            parsed.sort(key=lambda m: m.created_at or 0)
        prev = out.get(item_id)
        if prev is None or len(parsed) > len(prev):
            out[item_id] = parsed
    return out


def _adopt_sale(raw: dict[str, Any], item_id: str) -> Pursuit | None:
    for row in raw.get("conversations") or []:
        if not isinstance(row, dict):
            continue
        item = row.get("item") or {}
        if not isinstance(item, dict) or str(item.get("hash") or "") != item_id:
            continue
        if not item.get("is_mine"):
            return None
        price = item.get("price") or {}
        amount = price.get("amount") if isinstance(price, dict) else None
        if not isinstance(amount, (int, float)) or amount <= 0:
            return None
        title = str(item.get("title") or item_id)
        slug = str(item.get("slug") or "")
        return Pursuit(
            item_id=item_id,
            title=title,
            url=f"https://es.wallapop.com/item/{slug}" if slug else "",
            side="sell",
            ask_eur=float(amount),
            offer_eur=float(amount),
            walk_away_eur=float(amount),
            query=title,
            status="open",
            why="Your listing. Desk holds the asking price unless you set a floor at publish.",
        )
    return None
