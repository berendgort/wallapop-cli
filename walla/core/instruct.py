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
        "tagline": "look · offer · talk",
        "example": (
            "Human: find a used kite near Barcelona under 400eur, message "
            "seller, offer if GRAB. Agent: walla setup --budget 400 "
            "--aggression fair --must 'kite' -> search -> negotiate draft "
            "-> human approves text+EUR -> say/offer --yes. Never pay."
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
                    "step": "negotiate",
                    "agent": "walla negotiate <id> --json draft",
                    "ask_human": "approve the Spanish text",
                },
                {
                    "step": "say",
                    "agent": (
                        "never alone. walla chat <item_id> opens the listing Chat "
                        "button. walla say <item_id_or_conv> \"…\" --yes sends text."
                    ),
                    "ask_human": "yes to that exact text, then walla say --yes",
                },
                {
                    "step": "offer",
                    "agent": (
                        "never alone; refuse if EUR > budget. "
                        "On 409 offer-disabled: send the EUR in chat text instead."
                    ),
                    "ask_human": "yes to that exact EUR, then walla offer --yes",
                },
                {
                    "step": "pay_or_buy",
                    "agent": "never",
                    "ask_human": "human finishes pay/meet in the Wallapop app",
                },
            ],
            "never_pay": True,
            "yes_means": "send chat or price offer only; never complete purchase",
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
            "Draft with walla negotiate; never say/offer without human --yes; never pay.",
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
                "walla chat <item_id> --json",
                "walla negotiate <id> --json",
                "walla inbox --json",
                "walla thread <id> --json",
                'walla say <item_or_conv> "…" --yes',
            ],
            "offer": [
                "walla negotiate <id> --json",
                "walla offer <id> --eur <n> --yes",
            ],
        },
        "rules": [
            "Always present Wallapop shortlists ranked best-first with markdown item links.",
            "search / item / inbox / negotiate are safe reads or drafts.",
            "say and offer require --yes / confirm=true; name listing + euros.",
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
