"""Next negotiation step from a thread. Pure: no HTTP, no sends."""

from __future__ import annotations

import math
import re
from typing import Literal

from pydantic import BaseModel

from walla.hunter.negotiate import BANNED_PHRASES
from walla.hunter.pursuits import Pursuit
from walla.models.account import Message

__all__ = (
    "Move",
    "next_move",
)

_EUR = re.compile(r"(\d{1,5}(?:[.,]\d{1,2})?)\s*(?:€|eur(?:os)?)", re.IGNORECASE)
_DEJO = re.compile(
    r"(?:dejo|dejamos|bajo a|subo a|puedo(?: llegar)?(?: a)?)"
    r"\s+(?:en\s+)?(\d{1,5}(?:[.,]\d{1,2})?)",
    re.IGNORECASE,
)
_ACCEPT = re.compile(r"\b(vale|hecho|acepto|de acuerdo|perfecto|cerrado|trato)\b", re.IGNORECASE)
_QUESTION = re.compile(
    r"[?¿]|\b("
    r"medidas?|capacidad|marca|modelo|incluye|llevan?|tiene|"
    r"cu[aá]nto|cu[aá]ndo|d[oó]nde|c[oó]mo|qu[eé]|qui[eé]n|"
    r"disponible|envio|env[ií]o|recogida|fotos?"
    r")\b",
    re.IGNORECASE,
)


class Move(BaseModel):
    action: Literal["send", "wait", "converged", "walk"]
    text: str = ""
    offer_eur: float | None = None
    agreed_eur: float | None = None
    why: str
    nudges: int = 0


def next_move(pursuit: Pursuit, messages: list[Message]) -> Move:
    """Decide one step. Last message is the newest. Does not send."""
    if pursuit.status == "converged":
        return Move(
            action="converged",
            agreed_eur=pursuit.agreed_eur,
            offer_eur=pursuit.offer_eur,
            why=pursuit.why or "Already agreed. Human finishes in the app when ready.",
            nudges=pursuit.nudges,
        )
    if pursuit.status == "walked":
        return Move(
            action="walk",
            offer_eur=pursuit.offer_eur,
            why=pursuit.why or "Already stopped. No further messages.",
            nudges=pursuit.nudges,
        )
    thread = [m for m in messages if (m.text or "").strip()]
    ours = [m for m in thread if m.from_self]
    if not ours:
        if pursuit.status == "waiting":
            return Move(
                action="wait",
                offer_eur=pursuit.offer_eur,
                why="Opening already sent. Inbox has not echoed it yet.",
                nudges=pursuit.nudges,
            )
        text = _opening(pursuit)
        return Move(
            action="send",
            text=text,
            offer_eur=pursuit.offer_eur,
            why="First contact. Send the number; do not ask the human to type it.",
            nudges=pursuit.nudges,
        )
    if thread[-1].from_self:
        return Move(
            action="wait",
            offer_eur=pursuit.offer_eur,
            why="Last message is ours. Wait for the other person.",
            nudges=pursuit.nudges,
        )
    fresh = _after_us(thread)
    price = _latest_price(fresh)
    if price is not None:
        return _on_price(pursuit, price)
    fresh_text = " ".join(m.text for m in fresh)
    if _accepts(fresh_text):
        return Move(
            action="converged",
            agreed_eur=pursuit.offer_eur,
            offer_eur=pursuit.offer_eur,
            why=(
                f"They accepted {_fmt(pursuit.offer_eur)} EUR. "
                "Stop pitching. Human finishes in the app when ready."
            ),
            nudges=pursuit.nudges,
        )
    if _asks_question(fresh_text):
        return Move(
            action="wait",
            offer_eur=pursuit.offer_eur,
            why=(
                "They asked a question. Answer it in their words. "
                "Do not push a price close."
            ),
            nudges=pursuit.nudges,
        )
    if pursuit.nudges >= 1:
        return Move(
            action="wait",
            offer_eur=pursuit.offer_eur,
            why="Already asked once for a number. Do not send another nudge.",
            nudges=pursuit.nudges,
        )
    text = _nudge(pursuit)
    return Move(
        action="send",
        text=text,
        offer_eur=pursuit.offer_eur,
        why="They wrote without a number. Soft ask once, then wait.",
        nudges=pursuit.nudges + 1,
    )


def _on_price(pursuit: Pursuit, price: float) -> Move:
    ceiling = pursuit.walk_away_eur
    if pursuit.side == "buy" and price <= ceiling + 0.01:
        return Move(
            action="converged",
            agreed_eur=price,
            offer_eur=pursuit.offer_eur,
            why=(
                f"They named {_fmt(price)} EUR, within the {_fmt(ceiling)} ceiling. "
                "Stop writing. Human finishes in the app when ready."
            ),
            nudges=pursuit.nudges,
        )
    if pursuit.side == "sell" and price >= ceiling - 0.01:
        return Move(
            action="converged",
            agreed_eur=price,
            offer_eur=pursuit.offer_eur,
            why=(
                f"Buyer named {_fmt(price)} EUR, at or above the {_fmt(ceiling)} floor. "
                "Stop writing. Human accepts in the app when ready."
            ),
            nudges=pursuit.nudges,
        )
    nxt = _step(pursuit, price)
    if nxt is None:
        return Move(
            action="walk",
            offer_eur=pursuit.offer_eur,
            why=(
                f"Their {_fmt(price)} EUR is past the "
                f"{'ceiling' if pursuit.side == 'buy' else 'floor'} "
                f"{_fmt(ceiling)}, and the number cannot move further."
            ),
            nudges=pursuit.nudges,
        )
    text = _counter(pursuit, nxt)
    if any(phrase in text.lower() for phrase in BANNED_PHRASES):
        return Move(action="wait", why="Counter failed the tone check.", nudges=pursuit.nudges)
    return Move(
        action="send",
        text=text,
        offer_eur=nxt,
        why=f"Counter at {_fmt(nxt)} EUR toward their {_fmt(price)}.",
        nudges=pursuit.nudges,
    )


def _step(pursuit: Pursuit, theirs: float) -> float | None:
    current = pursuit.offer_eur
    if pursuit.side == "buy":
        target = min(pursuit.walk_away_eur, current + (theirs - current) / 2)
        if target >= 50:
            target = float(math.floor(target))
        target = round(min(target, pursuit.walk_away_eur), 2)
        if target <= current + 0.5:
            return None
        return target
    target = max(pursuit.walk_away_eur, current - (current - theirs) / 2)
    if target >= 50:
        target = float(math.floor(target))
    target = round(max(target, pursuit.walk_away_eur), 2)
    if target >= current - 0.5:
        return None
    return target


def _after_us(messages: list[Message]) -> list[Message]:
    last_us = max(i for i, m in enumerate(messages) if m.from_self)
    return messages[last_us + 1 :]


def _latest_price(messages: list[Message]) -> float | None:
    found: float | None = None
    for msg in messages:
        for match in (*_EUR.finditer(msg.text), *_DEJO.finditer(msg.text)):
            found = float(match.group(1).replace(",", "."))
    return found


def _accepts(text: str) -> bool:
    if re.search(r"\bno\b", text, re.IGNORECASE):
        return False
    return _ACCEPT.search(text) is not None


def _asks_question(text: str) -> bool:
    return _QUESTION.search(text) is not None


def _opening(pursuit: Pursuit) -> str:
    thing = " ".join(pursuit.title.split()[:6])[:60]
    eur = _fmt(pursuit.offer_eur)
    if pursuit.side == "sell":
        return f"Hola, {thing} sigue disponible. Lo dejo en {eur} €."
    return (
        f"Hola, me interesa tu {thing}. ¿Sigue disponible? "
        f"Te propongo {eur} €."
    )


def _nudge(pursuit: Pursuit) -> str:
    eur = _fmt(pursuit.offer_eur)
    if pursuit.side == "sell":
        return f"Gracias por escribir. El precio es {eur} €. ¿Te encaja?"
    return f"Gracias. ¿Te vendría bien {eur} €?"


def _counter(pursuit: Pursuit, eur: float) -> str:
    n = _fmt(eur)
    if pursuit.side == "sell":
        return f"Gracias. Te lo puedo dejar en {n} €. ¿Qué te parece?"
    return f"Gracias por contestar. Puedo llegar a {n} €. ¿Te parece bien?"


def _fmt(n: float) -> str:
    if float(n).is_integer():
        return str(int(n))
    return f"{n:.2f}"
