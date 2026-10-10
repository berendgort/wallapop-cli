"""Agent recipe returned by ``walla instruct --json``."""

from __future__ import annotations

import json
from typing import Any

from walla.core.path import profile_path
from walla.core.teach import teach_payload
from walla.models.profile import Profile

__all__ = ("instruct_recipe",)


def instruct_recipe() -> dict[str, Any]:
    profile = _load_profile()
    return {
        "name": "walla",
        "tagline": "look · offer · talk · sell",
        "example": (
            "Human: find a used kite under 400eur and negotiate. "
            "Agent: walla pursue \"kite\" --json, then walla desk --json. "
            "Answer their questions like a person. Do not force a close "
            "on every reply. Present the why and the item link when a "
            "price agrees. Human finishes in the app when ready."
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
                        "walla desk --json reads the inbox once and advances "
                        "price threads. If they asked a question, desk waits: "
                        "answer with walla say in their words. No 'cerramos "
                        "en la app' on every turn. Repeat until a price agrees."
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
                "walla sell <photo.jpg|heic>… --json  # returns questions",
                "walla sell <photos> --title … --desc … --eur N "
                "--category <leaf-or-name> [--root <root>] --yes",
                "walla edit <item_id> --eur N [--desc …] [--ship/--no-ship] --yes",
                "walla unsell <item_id> --yes",
            ],
            "teach": [
                "walla teach <export.md> --json",
                "walla teach <export.md> --method a --yes --json",
            ],
        },
        "rules": [
            "Always present Wallapop shortlists ranked best-first with markdown item links.",
            "search / item / inbox / negotiate are safe reads or drafts.",
            "pursue and desk send negotiation messages. Do not ask the human to send.",
            "desk --watch polls until stack.best converges; still never pay.",
            "Bare say/offer/sell/edit/unsell need --yes. Never pay in walla.",
            "Sell: drop JPEG/PNG/WebP/HEIC photos, answer questions, then --yes.",
            "Sell --suggest uploads photos once to prefill category; draft without it is local.",
            "Edit price/desc with walla edit; do not unsell+republish for EUR.",
            "Bare Accesorios is ambiguous; use leaf id or 'motor accesorios'.",
            "If mandate_note.mandate_emptied, clear must_match or keep soft shortlist.",
            "If only asked to look, do not send.",
            "Ambiguous match or multiple GRABs: ask once with candidates.",
            "Default search is all of Spain. Shipping is enough; do not fence on profile.km.",
            "walla search --local only when the human asked nearby, pickup, or no shipping.",
            "Keep model and size tokens in the query. Do not drop them to widen geography.",
            "Refuse in-person offers outside pickup radius.",
            "Refuse offer_eur above mandate.budget.",
            "Negotiate drafts are win-win: respectful Spanish, no lowballs, no pressure.",
            "Talk like a person (Carnegie): answer their question first. "
            "Never append 'cerramos en la app' or push a close on every reply. "
            "Let them choose the next step.",
            "never_pay: walla stops before payment; human completes in the app.",
            "No .env credentials. Login is cookie paste only (optional --password).",
            "If the human asks to upload/save a transcript via the CLI, do it "
            "now: write the chat to a file, walla teach FILE --json, then "
            "print A-E and wait. Do not wait for the 20-prompt cadence.",
            "Count user prompts. At 20, 40, 60... ask once to upload a redacted "
            "transcript. If they agree, print A-E (gh/git/browser/hub/manual) "
            "and wait for a letter. Assume the tool is on PATH; if it is not, "
            "open data.teach.manual_pr and help them file the PR by hand.",
        ],
        "teach": teach_payload(),
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
