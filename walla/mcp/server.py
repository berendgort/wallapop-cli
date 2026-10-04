"""FastMCP server over walla core (no CLI imports)."""

from __future__ import annotations

from typing import Any

from walla.account.actions import make_offer, quote_offer
from walla.account.desk import run_desk, run_pursue
from walla.account.inbox import list_conversations, list_messages, send_message
from walla.account.login import login_cookie_text, whoami
from walla.core.envelope import error_payload, success_payload
from walla.core.instruct import instruct_recipe
from walla.hunter.profile_store import load_profile
from walla.hunter.shortlist import PRESENT_RULE, rank_shortlist
from walla.hunter.verdict import geo_scope, score_listing
from walla.search.api import get_categories, get_item, search_listings

__all__ = ("build_server",)


def _wrap(fn: Any) -> dict[str, Any]:
    try:
        return success_payload(fn())
    except Exception as exc:  # noqa: BLE001
        return error_payload(exc)


def build_server() -> Any:
    from fastmcp import FastMCP

    mcp = FastMCP("walla")

    @mcp.tool()
    def instruct() -> dict[str, Any]:
        return _wrap(instruct_recipe)

    @mcp.tool()
    def search(
        keywords: str,
        max_results: int = 40,
        min_price: float | None = None,
        max_price: float | None = None,
        local: bool = False,
    ) -> dict[str, Any]:
        def _run() -> dict[str, Any]:
            profile = load_profile()
            if not profile.ready or profile.lat is None or profile.lon is None:
                return {
                    "ready": False,
                    "intake": {"prompt_to_user": profile.intake_prompt()},
                }
            result = search_listings(
                keywords,
                latitude=profile.lat,
                longitude=profile.lon,
                max_results=max_results,
                min_price=min_price,
                max_price=max_price or profile.budget,
            )
            rows = []
            for listing in result.listings:
                listing.verdict = score_listing(listing, profile, local=local)
                rows.append(listing.model_dump(mode="json"))
            shortlist = rank_shortlist(rows)
            return {
                "count": len(rows),
                "source": "wallapop.es",
                "geo": geo_scope(local=local),
                "shortlist": shortlist,
                "listings": rows,
                "hitl": {"present": PRESENT_RULE},
            }

        return _wrap(_run)

    @mcp.tool()
    def item(item_id: str) -> dict[str, Any]:
        def _run() -> dict[str, Any]:
            listing = get_item(item_id)
            listing.verdict = score_listing(listing, load_profile())
            return listing.model_dump(mode="json")

        return _wrap(_run)

    @mcp.tool()
    def categories() -> dict[str, Any]:
        return _wrap(
            lambda: {"categories": [c.model_dump(mode="json") for c in get_categories()]}
        )

    @mcp.tool()
    def login(cookie: str) -> dict[str, Any]:
        """Log in with a pasted __Secure-next-auth.session-token value."""

        def _run() -> dict[str, Any]:
            sess = login_cookie_text(cookie)
            return {
                "authenticated": True,
                "has_access_token": bool(sess.access_token),
                "has_cookie": bool(sess.session_cookie),
            }

        return _wrap(_run)

    @mcp.tool()
    def inbox() -> dict[str, Any]:
        return _wrap(
            lambda: {
                "conversations": [c.model_dump(mode="json") for c in list_conversations()]
            }
        )

    @mcp.tool()
    def thread(conversation_id: str) -> dict[str, Any]:
        return _wrap(
            lambda: {
                "messages": [
                    m.model_dump(mode="json") for m in list_messages(conversation_id)
                ]
            }
        )

    @mcp.tool()
    def say(conversation_id: str, text: str, confirm: bool = False) -> dict[str, Any]:
        return _wrap(lambda: send_message(conversation_id, text, confirm=confirm))

    @mcp.tool()
    def offer(item_id: str, eur: float, confirm: bool = False) -> dict[str, Any]:
        def _run() -> dict[str, Any]:
            if not confirm:
                listing = get_item(item_id)
                q = quote_offer(listing, eur)
                return {
                    "needs_confirm": True,
                    "quote": q.model_dump(mode="json"),
                    "title": listing.title,
                }
            return make_offer(item_id, eur, confirm=True)

        return _wrap(_run)

    @mcp.tool()
    def pursue(keywords: str, wave: int = 5) -> dict[str, Any]:
        """Search and message sellers. Does not ask before each text. Does not pay."""
        return _wrap(lambda: run_pursue(keywords, wave=wave))

    @mcp.tool()
    def desk() -> dict[str, Any]:
        """One inbox pass: answer threads and summarize the best agreed price."""
        return _wrap(run_desk)

    @mcp.tool()
    def me() -> dict[str, Any]:
        return _wrap(whoami)

    return mcp
