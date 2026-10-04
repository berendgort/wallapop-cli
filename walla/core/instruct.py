"""Agent recipe returned by ``walla instruct --json``."""

from __future__ import annotations

import json
from typing import Any

from walla.core.path import profile_path
from walla.models.profile import Profile

__all__ = ("instruct_recipe",)


def instruct_recipe() -> dict[str, Any]:
    profile = _load_profile()
    return {
        "name": "walla",
        "tagline": "look · offer · talk · sell",
        "example": (
            "Human: find a used kite under 400eur and negotiate. "
            "Agent: walla pursue \"kite\" --json, then walla desk --json "
            "until stack.best is set. Present the why and the item link. "
            "Do not ask the human to send messages. Human closes in the app."
        ),
        "mandate": {
            "budget": profile.spend_cap,
            "aggressiveness": profile.aggressiveness,
            "must_match": profile.must_match,
            "ready": profile.ready,
            "how": (
                "walla setup --lat … --lon … --budget N "
                "--aggression soft|fair|firm --must 'word1 word2'"
            ),
        },
        "hitl": {
            "ladder": [
                {
                    "step": "search",
                    "agent": (
                        "alone, Spain-wide, inside budget + must_match. "
                        "Keep model and size in the keywords. "
                        "--local only if the human asked nearby or pickup."
                    ),
                    "ask_human": "only if query vague or budget unset",
                },
                {
                    "step": "shortlist",
                    "agent": (
                        "Say these are Wallapop.es results. Show numbered "
                        "data.shortlist best-first with markdown links on every "
                        "https://es.wallapop.com/item/… URL. Never omit links."
                    ),
                    "ask_human": "if more than one GRAB, human picks the id",
                },
                {
                    "step": "pursue",
                    "agent": (
                        "walla pursue \"<query>\" --json sends the opening wave. "
                        "Do not ask the human to approve each text."
                    ),
                    "ask_human": "never for the messages",
                },
                {
                    "step": "desk",
                    "agent": (
                        "walla desk --json reads the inbox once, replies, "
                        "and returns stack.best plus why. Repeat until a price agrees."
                    ),
                    "ask_human": "never for the messages",
                },
                {
                    "step": "offer",
                    "agent": (
                        "Prefer chat text from pursue/desk. "
                        "walla offer --yes only if a formal offer is required. "
                        "On 409, the EUR stays in the chat text."
                    ),
                    "ask_human": "never during pursue/desk",
                },
                {
                    "step": "pay_or_buy",
                    "agent": "never",
                    "ask_human": "human finishes pay/meet in the Wallapop app",
                },
            ],
            "never_pay": True,
            "yes_means": (
                "bare say/offer/sell still need --yes. "
                "pursue and desk send negotiation chat without asking. "
                "never complete purchase"
            ),
        },
        "protocol": [
            "Install from PyPI: pipx install 'walla-cli[mcp]' "
            "(https://pypi.org/project/walla-cli/). Clone only if hacking.",
            "walla doctor --json - never print tokens or cookies.",
            "If no session: ask the human to run `walla login` and paste "
            "__Secure-next-auth.session-token (or pass --cookie for non-interactive).",
            "If mandate.budget is null: ask once for budget + aggression + must words.",
            "Do the ask with walla … --json. Always narrate as Wallapop.es "
            "and paste data.shortlist with full item URLs (markdown links).",
            "Negotiate with walla pursue and walla desk. Do not ask the human "
            "to send or approve each message. Never pay.",
        ],
        "present": {
            "channel": "wallapop.es",
            "format": (
                "1. GRAB · Title · €N · City\n"
                "   [open on Wallapop](https://es.wallapop.com/item/<web_slug>)"
            ),
            "order": "best-first: GRAB then LOOK; lower EUR within band",
            "rule": (
                "Every shortlist row must include the full item URL. "
                "Never table-only without links."
            ),
        },
        "verbs": {
            "look": [
                "walla search <q> --json",
                "walla search <q> --local --json",
                "walla item <id> --json",
            ],
            "talk": [
                'walla pursue "<query>" --json',
                "walla desk --json",
                "walla desk --watch --seconds 45 --rounds 12 --json",
                "walla negotiate <id> --json",
                "walla inbox --json",
            ],
            "offer": [
                "walla negotiate <id> --json",
                "walla offer <id> --eur <n> --yes",
            ],
            "sell": [
                "walla categories --find <name> --json",
                "walla sell <photos> --title … --suggest --json",
                "walla sell <photo.jpg>… --json  # returns questions",
                "walla sell <photos> --title … --desc … --eur N "
                "--category <leaf-or-name> [--root <root>] --yes",
                "walla unsell <item_id> --yes",
            ],
        },
        "rules": [
            "Always present Wallapop shortlists ranked best-first with markdown item links.",
            "search / item / inbox / negotiate are safe reads or drafts.",
            "pursue and desk send negotiation messages. Do not ask the human to send.",
            "desk --watch polls until stack.best converges; still never pay.",
            "Bare say, offer, and sell still need --yes. Never pay or accept in walla.",
            "Sell: drop photos, ask data.questions, then publish with --yes only.",
            "Sell --suggest prefills category from Wallapop steps when title is set.",
            "If only asked to look, do not send.",
            "Ambiguous match or multiple GRABs: ask once with candidates.",
            "Default search is all of Spain. Shipping is enough; do not fence on profile.km.",
            "walla search --local only when the human asked nearby, pickup, or no shipping.",
            "Keep model and size tokens in the query. Do not drop them to widen geography.",
            "Refuse in-person offers outside pickup radius.",
            "Refuse offer_eur above mandate.budget.",
            "Negotiate drafts are win-win: respectful Spanish, no lowballs, no pressure.",
            "never_pay: walla stops before payment; human completes in the app.",
            "No .env credentials. Login is cookie paste only (optional --password).",
        ],
        "envelope": ["ok", "api_version", "data | error / error_type / retryable"],
        "standards": [
            "docs/code_quality.md",
            "docs/data_engineering_standards.md",
            "docs/WIRE.md",
        ],
    }


def _load_profile() -> Profile:
    p = profile_path()
    if not p.is_file():
        return Profile()
    try:
        return Profile.model_validate(json.loads(p.read_text(encoding="utf-8")))
    except (OSError, ValueError, json.JSONDecodeError):
        return Profile()
