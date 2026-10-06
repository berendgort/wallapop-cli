"""Park agent transcripts locally (no Wallapop I/O)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from walla.core.path import teach_dir, teach_state_path
from walla.core.teach_pr import MANUAL_PR, method_menu

__all__ = (
    "ASK_EVERY",
    "FIRST_NOTICE",
    "ask_copy",
    "consume_first_notice",
    "park_transcript",
    "redact_secrets",
    "should_ask_feedback",
    "teach_payload",
)

ASK_EVERY = 20

FIRST_NOTICE = (
    "Long agent chats (especially hunts) help improve walla. After you confirm, "
    "the agent can open a PR with walla teach --method A-E (gh/git/browser/hub/"
    "manual). Tools are assumed on PATH; otherwise open "
    f"{MANUAL_PR} yourself."
)

_SECRET = re.compile(
    r"(?i)("
    r"(?:__secure-next-auth\.session-token|session-token|bearer|refresh_token)"
    r"['\"=\s:]+[^\s'\"]+"
    r"|eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+"
    r")"
)


def redact_secrets(text: str) -> tuple[str, int]:
    """Replace session cookies, bearers, and JWTs. Returns text, hit count."""
    hits = 0

    def _sub(match: re.Match[str]) -> str:
        nonlocal hits
        hits += 1
        return "[redacted]"

    return _SECRET.sub(_sub, text), hits


def park_transcript(text: str, *, name: str | None = None) -> dict[str, Any]:
    """Write a redacted copy under ~/.config/walla/teach/."""
    body, n_redacted = redact_secrets(text)
    if not body.strip():
        raise ValueError("transcript is empty")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", (name or "chat").strip())[:40]
    dest = teach_dir() / f"{stamp}-{safe or 'chat'}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body, encoding="utf-8")
    return {
        "path": str(dest),
        "bytes": dest.stat().st_size,
        "redacted": n_redacted,
        "how": f"parked locally; PR via walla teach --method a --yes or {MANUAL_PR}",
        "manual_pr": MANUAL_PR,
    }


def should_ask_feedback(user_prompts: int, *, last_asked_band: int = 0) -> bool:
    """True at 20, 40, 60... once per band (count >= 20)."""
    if user_prompts < ASK_EVERY:
        return False
    band = (user_prompts // ASK_EVERY) * ASK_EVERY
    return band > last_asked_band


def ask_copy(user_prompts: int) -> str:
    return (
        f"This chat is {user_prompts} prompts in. Upload a redacted transcript "
        "to improve walla? If yes, reply with A B C D or E (gh / git / browser "
        f"/ hub / I'll do it). Manual PR: {MANUAL_PR}"
    )


def _load_state() -> dict[str, Any]:
    path = teach_state_path()
    if not path.is_file():
        return {"schema_version": 1, "first_notice_at": None}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {"schema_version": 1, "first_notice_at": None}
    return raw if isinstance(raw, dict) else {"schema_version": 1}


def _save_state(state: dict[str, Any]) -> None:
    path = teach_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def consume_first_notice() -> str | None:
    """Return the first-use blurb once, then persist that it was shown."""
    state = _load_state()
    if state.get("first_notice_at"):
        return None
    state["first_notice_at"] = datetime.now(timezone.utc).isoformat()
    _save_state(state)
    return FIRST_NOTICE


def teach_payload() -> dict[str, Any]:
    """Instruct/doctor field. Never attach this to search/desk envelopes."""
    notice = consume_first_notice()
    return {
        "dir": str(teach_dir()),
        "how": "walla teach <export.md> --method a --yes --json",
        "ask_every": ASK_EVERY,
        "first_notice": notice,
        "confirm": "Ask yes/no before any upload. Never dump the transcript unasked.",
        "methods": method_menu(),
        "manual_pr": MANUAL_PR,
        "ask_rule": (
            "Count user prompts. At 20, 40, 60... ask once to upload. "
            "If yes, print A-E and wait for a letter. Assume gh/git/hub/"
            "browser is installed; on failure open data.teach.manual_pr "
            "and walk them through a manual PR. Never on search/desk."
        ),
        "ask_copy": ask_copy(ASK_EVERY),
        "cli": (
            "Save the chat to a file, then: "
            "walla teach FILE --method a|b|c|d|e --yes --json"
        ),
    }
