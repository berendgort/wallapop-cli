"""Rank agreed deals. The human still closes in the app."""

from __future__ import annotations

from walla.hunter.pursuits import Pursuit

__all__ = ("stack_summary",)


def stack_summary(pursuits: list[Pursuit]) -> dict[str, object]:
    buys = [p for p in pursuits if p.side == "buy" and p.status == "converged"]
    sells = [p for p in pursuits if p.side == "sell" and p.status == "converged"]
    buys.sort(key=lambda p: (p.agreed_eur if p.agreed_eur is not None else 1e18, p.title))
    sells.sort(key=lambda p: (-(p.agreed_eur or 0), p.title))
    best = buys[0] if buys else (sells[0] if sells else None)

    def rows(status: str) -> list[dict[str, object]]:
        return [p.model_dump(mode="json") for p in pursuits if p.status == status]

    return {
        "best": best.model_dump(mode="json") if best else None,
        "why": _why(best),
        "buy_converged": [p.model_dump(mode="json") for p in buys],
        "sell_converged": [p.model_dump(mode="json") for p in sells],
        "waiting": rows("waiting") + rows("open"),
        "walked": rows("walked"),
        "tracked": len(pursuits),
        "close_in_app": True,
        "never_pay": True,
    }


def _why(best: Pursuit | None) -> str:
    if best is None:
        return (
            "No price agreed yet. Threads are in waiting. "
            "You close any deal in the Wallapop app."
        )
    agreed = _fmt(best.agreed_eur or best.offer_eur)
    if best.side == "buy":
        return (
            f"{best.title} at {agreed} EUR. Ask was {_fmt(best.ask_eur)}, "
            f"ceiling {_fmt(best.walk_away_eur)}. Cheapest agreed price. "
            f"{best.url} Close it in the Wallapop app."
        )
    return (
        f"Buyer on {best.title} at {agreed} EUR. Floor {_fmt(best.walk_away_eur)}. "
        f"Highest agreed price. {best.url} Accept it in the Wallapop app."
    )


def _fmt(n: float) -> str:
    if float(n).is_integer():
        return str(int(n))
    return f"{n:.2f}"
