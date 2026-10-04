"""Agent recipe returned by ``walla instruct --json``."""

from __future__ import annotations

from typing import Any

__all__ = ("instruct_recipe",)


def instruct_recipe() -> dict[str, Any]:
    return {
        "name": "walla",
        "tagline": "look · offer · talk",
        "protocol": [
            "Install: pipx install -e '.[mcp]' in the clone (private repo).",
            "walla doctor --json - never print credentials.",
            "If no session: walla login --json (reads WALLAPOP_USER / WALLAPOP_PW).",
            "On auth failure: follow human_fix cookie export, then login --cookies.",
            "Do the ask with walla … --json and narrate in prose.",
        ],
        "verbs": {
            "look": ["walla search <q> --json", "walla item <id> --json"],
            "talk": [
                "walla inbox --json",
                "walla thread <id> --json",
                "walla say <id> <text> --yes",
            ],
            "offer": ["walla offer <id> --eur <n> --yes"],
        },
        "rules": [
            "search / item / inbox are safe reads.",
            "say and offer require --yes / confirm=true; name listing + euros.",
            "If only asked to look, do not send.",
            "Ambiguous match: ask once with candidates.",
            "Refuse in-person offers outside pickup radius.",
        ],
        "envelope": ["ok", "api_version", "data | error / error_type / retryable"],
        "standards": [
            "docs/code_quality.md",
            "docs/data_engineering_standards.md",
            "docs/WIRE.md",
        ],
    }
