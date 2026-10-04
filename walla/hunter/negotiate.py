"""Win-win negotiation drafts (pure; no HTTP)."""

from __future__ import annotations

import math
import re

from pydantic import BaseModel

from walla.hunter.verdict import haversine_km, score_listing
from walla.models.listing import Listing
from walla.models.profile import Aggression, Profile

__all__ = (
    "BANNED_PHRASES",
    "NegotiationBrief",
    "draft_negotiation",
)

BANNED_PHRASES = (
    "ridicul",
    "absurdo",
    "estafa",
    "demasiado caro",
    "last chance",
    "ultima oportunidad",
    "urgente",
    "otros interesados",
    "tengo otra oferta",
    "take it or leave",
)

_AGGRESSION_PCT: dict[Aggression, float] = {
    "soft": 0.95,
    "fair": 0.90,
    "firm": 0.80,
}


class NegotiationBrief(BaseModel):
    item_id: str
    title: str
    url: str
    ask_eur: float
    offer_eur: float
    walk_away_eur: float
    verdict: str
    opening: str
    offer_line: str
    why: str
    seller_gives: str
    you_give: str
    tone_checks: list[str]
    needs_confirm: bool = True
    hitl: str = "approve_text_and_eur"
    hint: str = (
        "Draft only. Human must approve text + EUR, then walla say / offer --yes. "
        "Never pay or finish the purchase in walla."
    )


def draft_negotiation(
    listing: Listing,
    profile: Profile,
    *,
    seller_name: str | None = None,
) -> NegotiationBrief:
    """Build a respectful Spanish draft. Never sends."""
    if profile.spend_cap is None:
        raise ValueError(
            "hitl: set_budget - run walla setup --budget N before negotiating"
        )
    _assert_reachable(listing, profile)
    ask = float(listing.price.amount)
    if ask > profile.spend_cap:
        raise ValueError(
            f"Ask {_fmt_eur(ask)} EUR exceeds budget {_fmt_eur(profile.spend_cap)} EUR"
        )
    verdict = score_listing(listing, profile)
    if verdict == "PASS":
        raise ValueError(
            f"Listing is PASS under mandate (must_match / budget / radius): {listing.title}"
        )
    walk = _walk_away(ask, profile)
    offer = _first_offer(ask, walk, verdict, profile.aggressiveness)
    specific = _specific_thing(listing)
    greeting = f"Hola {seller_name}," if seller_name else "Hola,"
    opening, offer_line, you_give = _copy(greeting, specific, offer, _ships(listing))
    return NegotiationBrief(
        item_id=listing.id,
        title=listing.title,
        url=listing.url,
        ask_eur=ask,
        offer_eur=offer,
        walk_away_eur=walk,
        verdict=verdict,
        opening=opening,
        offer_line=offer_line,
        why=_why(ask, offer, verdict, profile.aggressiveness),
        seller_gives="Un precio justo y una venta rapida sin pelea.",
        you_give=you_give,
        tone_checks=_tone_checks(opening, offer_line, offer, ask),
    )


def _ships(listing: Listing) -> bool:
    return bool(listing.user_allows_shipping or listing.shippable)


def _copy(greeting: str, specific: str, offer: float, ships: bool) -> tuple[str, str, str]:
    if ships:
        opening = (
            f"{greeting} me interesa tu {specific}. "
            "¿Sigue disponible? Me iría bien envío Wallapop."
        )
        offer_line = (
            f"Gracias. Por el estado y lo que hay ahora mismo, te propongo "
            f"{_fmt_eur(offer)} € con envío Wallapop."
        )
        return opening, offer_line, "Envío Wallapop, pago claro, trato respetuoso."
    opening = (
        f"{greeting} me interesa tu {specific}. "
        "¿Sigue disponible? Puedo pasar hoy si te va bien."
    )
    offer_line = (
        f"Gracias. Por el estado y lo que hay ahora mismo, te propongo "
        f"{_fmt_eur(offer)} € y lo recojo cuando te venga bien."
    )
    return opening, offer_line, "Recogida flexible, pago claro, trato respetuoso."


def _assert_reachable(listing: Listing, profile: Profile) -> None:
    if listing.user_allows_shipping or listing.shippable:
        return
    if (
        profile.lat is None
        or profile.lon is None
        or not listing.location
        or listing.location.latitude is None
        or listing.location.longitude is None
    ):
        return
    dist = haversine_km(
        profile.lat,
        profile.lon,
        listing.location.latitude,
        listing.location.longitude,
    )
    if dist > profile.pickup_km:
        raise ValueError(
            f"In-person listing outside pickup radius ({listing.title}). Refuse."
        )


def _walk_away(ask: float, profile: Profile) -> float:
    cap = profile.spend_cap
    if cap is None:
        return ask
    return round(min(cap, ask), 2)


def _first_offer(
    ask: float, walk: float, verdict: str, aggressiveness: Aggression
) -> float:
    """Aggression sets the ask percent; never below 80% on first message."""
    if ask <= 0:
        return 0.0
    pct = _AGGRESSION_PCT.get(aggressiveness, 0.90)
    if ask <= walk and verdict == "GRAB" and aggressiveness == "fair":
        pct = max(pct, 0.95)
    elif ask <= walk and verdict == "GRAB" and aggressiveness == "soft":
        pct = 0.98
    raw = ask * pct
    floor = ask * 0.80
    offer = max(floor, min(raw, walk, ask))
    if offer >= 50:
        offer = float(math.floor(offer))
    else:
        offer = round(offer, 0)
    return round(min(max(offer, floor), walk, ask), 2)


def _specific_thing(listing: Listing) -> str:
    title = listing.title.strip()
    words = re.findall(r"[\wÁÉÍÓÚÜÑáéíóúüñ-]+", title)
    if not words:
        return "anuncio"
    return " ".join(words[:5])[:60]


def _why(ask: float, offer: float, verdict: str, aggressiveness: Aggression) -> str:
    return (
        f"Aggression={aggressiveness}; first offer {_fmt_eur(offer)} EUR "
        f"(~{int(round(100 * offer / ask))}% of {_fmt_eur(ask)}), verdict {verdict}."
    )


def _fmt_eur(n: float) -> str:
    if float(n).is_integer():
        return str(int(n))
    return f"{n:.2f}"


def _tone_checks(opening: str, offer_line: str, offer: float, ask: float) -> list[str]:
    blob = f"{opening}\n{offer_line}".lower()
    checks = [
        "no_criticism",
        "specific_interest",
        "one_easy_question",
        "seller_interest_framed",
        "first_offer_ge_80pct_ask",
        "draft_only_needs_confirm",
        "never_pay_in_walla",
    ]
    if any(p in blob for p in BANNED_PHRASES):
        checks.append("FAIL_banned_phrase")
    if "¿sigue disponible?" not in blob and "sigue disponible" not in blob:
        checks.append("FAIL_missing_availability_question")
    if ask > 0 and offer < ask * 0.80 - 0.01:
        checks.append("FAIL_lowball")
    return checks
