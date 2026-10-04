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
                    "agent": "alone inside budget + radius + must_match",
                    "ask_human": "only if query vague or budget unset",
                },
                {
                    "step": "shortlist",
                    "agent": "show GRAB title, EUR, URL, verdict",
                    "ask_human": "if more than one GRAB, human picks the id",
                },
                {
                    "step": "negotiate",
                    "agent": "walla negotiate <id> --json draft",
                    "ask_human": "approve the Spanish text",
                },
                {
                    "step": "say",
                    "agent": "never alone",
                    "ask_human": "yes to that exact text, then walla say --yes",
                },
                {
                    "step": "offer",
                    "agent": "never alone; refuse if EUR > budget",
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
            "Do the ask with walla … --json and narrate in prose.",
            "Draft with walla negotiate; never say/offer without human --yes; never pay.",
        ],
        "verbs": {
            "look": ["walla search <q> --json", "walla item <id> --json"],
            "talk": [
                "walla negotiate <id> --json",
                "walla inbox --json",
                "walla thread <id> --json",
                "walla say <id> <text> --yes",
            ],
            "offer": [
                "walla negotiate <id> --json",
                "walla offer <id> --eur <n> --yes",
            ],
        },
        "rules": [
            "search / item / inbox / negotiate are safe reads or drafts.",
            "say and offer require --yes / confirm=true; name listing + euros.",
            "If only asked to look, do not send.",
            "Ambiguous match or multiple GRABs: ask once with candidates.",
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
